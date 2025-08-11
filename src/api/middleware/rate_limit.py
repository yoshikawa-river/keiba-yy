"""
レート制限ミドルウェア
"""

from typing import Any, Optional, Union
import asyncio
import hashlib
import logging
import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.config import settings
from src.api.exceptions.custom_exceptions import RateLimitException

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """インメモリレート制限実装（開発用）"""

    def __init__(self):
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.lock = asyncio.Lock()

    async def check_rate_limit(
        self, key: str, limit: int, window: int
    ) -> tuple[bool, int]:
        """
        レート制限チェック

        Returns:
            (制限内かどうか, 残りリクエスト数)
        """
        async with self.lock:
            now = time.time()
            window_start = now - window

            # 古いリクエストを削除
            self.requests[key] = [
                req_time for req_time in self.requests[key] if req_time > window_start
            ]

            # 現在のリクエスト数
            current_count = len(self.requests[key])

            if current_count >= limit:
                # レート制限超過
                return False, 0

            # リクエストを記録
            self.requests[key].append(now)

            return True, limit - current_count - 1

    async def get_reset_time(self, key: str, window: int) -> int:
        """リセット時刻を取得（秒）"""
        async with self.lock:
            if self.requests.get(key):
                oldest_request = min(self.requests[key])
                reset_time = int(oldest_request + window - time.time())
                return max(reset_time, 0)
            return 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """レート制限ミドルウェア"""

    def __init__(self, app, limiter: Optional[InMemoryRateLimiter] = None):
        super().__init__(app)
        self.limiter = limiter or InMemoryRateLimiter()

    def get_client_identifier(self, request: Request) -> str:
        """クライアント識別子を取得"""
        # 優先順位: APIキー > 認証トークン > IPアドレス

        # APIキー
        api_key = request.headers.get("x-api-key")
        if api_key:
            # APIキーの一部をハッシュ化
            return f"api:{hashlib.md5(api_key[:10].encode()).hexdigest()}"

        # 認証トークン
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # トークンの一部をハッシュ化
            token = auth_header[7:20]  # 最初の13文字
            return f"user:{hashlib.md5(token.encode()).hexdigest()}"

        # IPアドレス
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        return f"ip:{client_ip}"

    def get_rate_limit_config(self, request: Request) -> tuple[int, int]:
        """
        エンドポイントごとのレート制限設定を取得

        Returns:
            (リクエスト数制限, 時間窓（秒）)
        """
        path = request.url.path

        # エンドポイント別の設定
        endpoint_limits = {
            "/auth/login": (10, 60),  # 1分間に10回
            "/auth/register": (5, 60),  # 1分間に5回
            "/predictions/race": (100, 60),  # 1分間に100回
            "/predictions/batch": (10, 60),  # 1分間に10回
            "/ws": (50, 60),  # WebSocket接続は1分間に50回
        }

        # パスに基づいて制限を決定
        for endpoint, limits in endpoint_limits.items():
            if path.startswith(endpoint):
                return limits

        # デフォルト設定
        return (settings.rate_limit_requests, settings.rate_limit_period)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # レート制限が無効な場合はスキップ
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # 静的ファイルやヘルスチェックは除外
        if request.url.path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # クライアント識別子を取得
        client_id = self.get_client_identifier(request)

        # レート制限設定を取得
        limit, window = self.get_rate_limit_config(request)

        # レート制限チェック
        allowed, remaining = await self.limiter.check_rate_limit(
            client_id, limit, window
        )

        if not allowed:
            # リセット時刻を取得
            reset_after = await self.limiter.get_reset_time(client_id, window)

            logger.warning(
                f"Rate limit exceeded - "
                f"Client: {client_id}, "
                f"Path: {request.url.path}, "
                f"Reset after: {reset_after}s"
            )

            raise RateLimitException(retry_after=reset_after)

        # リクエスト処理
        response = await call_next(request)

        # レート制限情報をヘッダーに追加
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + window))

        return response


class APIKeyRateLimiter:
    """APIキー別のレート制限"""

    def __init__(self):
        self.api_key_limits = {
            # APIキーごとの個別制限設定
            # "sk_premium_key": (1000, 60),  # プレミアムキー: 1分1000回
            # "sk_basic_key": (100, 60),  # ベーシックキー: 1分100回
        }
        self.limiter = InMemoryRateLimiter()

    async def check_api_key_limit(self, api_key: str) -> tuple[bool, Optional[int]]:
        """
        APIキーのレート制限チェック

        Returns:
            (許可されるか, リトライまでの秒数)
        """
        # APIキー固有の制限を取得
        if api_key in self.api_key_limits:
            limit, window = self.api_key_limits[api_key]
        else:
            # デフォルト制限
            limit = settings.rate_limit_requests
            window = settings.rate_limit_period

        # レート制限チェック
        allowed, remaining = await self.limiter.check_rate_limit(
            f"api_key:{api_key}", limit, window
        )

        if not allowed:
            reset_after = await self.limiter.get_reset_time(
                f"api_key:{api_key}", window
            )
            return False, reset_after

        return True, None
