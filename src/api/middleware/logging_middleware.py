"""
ロギングミドルウェア
"""

import json
import logging
import time
import uuid
from collections.abc import Callable
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """リクエスト/レスポンスロギング用ミドルウェア"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # リクエストID生成
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 開始時刻
        start_time = time.time()

        # リクエスト情報をログ
        from typing import Any

        request_log: dict[str, Any] = {
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent", ""),
        }

        # APIキーやトークンの有無を記録（値は記録しない）
        if "authorization" in request.headers:
            request_log["has_auth"] = True
        if "x-api-key" in request.headers:
            request_log["has_api_key"] = True

        logger.info(f"Request: {json.dumps(request_log)}")

        # リクエスト処理
        from typing import cast

        response = cast(Response, await call_next(request))

        # 処理時間計算
        process_time = time.time() - start_time

        # レスポンス情報をログ
        response_log = {
            "request_id": request_id,
            "status_code": response.status_code,
            "process_time": round(process_time * 1000, 2),  # ミリ秒
        }

        # レスポンスヘッダーに情報を追加
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        # ログレベルを決定
        if response.status_code >= 500:
            logger.error(f"Response: {json.dumps(response_log)}")
        elif response.status_code >= 400:
            logger.warning(f"Response: {json.dumps(response_log)}")
        else:
            logger.info(f"Response: {json.dumps(response_log)}")

        return response


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """パフォーマンス監視ミドルウェア"""

    # 遅いリクエストの閾値（秒）
    SLOW_REQUEST_THRESHOLD = 1.0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # メモリ使用量の記録（必要に応じて）
        # import psutil
        # process = psutil.Process()
        # memory_before = process.memory_info().rss / 1024 / 1024  # MB

        from typing import cast

        response = cast(Response, await call_next(request))

        process_time = time.time() - start_time

        # 遅いリクエストを警告
        if process_time > self.SLOW_REQUEST_THRESHOLD:
            logger.warning(
                f"Slow request detected - "
                f"Path: {request.url.path}, "
                f"Method: {request.method}, "
                f"Time: {process_time:.2f}s"
            )

        # メトリクス収集（実際の実装では Prometheus などに送信）
        metrics = {
            "endpoint": f"{request.method} {request.url.path}",
            "status_code": response.status_code,
            "response_time": process_time,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # メトリクスをログ（または外部システムに送信）
        if process_time > 0.5:  # 500ms以上かかったリクエストのみ記録
            logger.info(f"Performance metrics: {json.dumps(metrics)}")

        return response
