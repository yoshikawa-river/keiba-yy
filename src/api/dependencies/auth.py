"""
認証関連の依存関数
"""

from typing import List, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from src.api.auth.jwt_handler import jwt_handler
from src.api.config import settings
from src.api.exceptions.custom_exceptions import (
    AuthenticationException,
    AuthorizationException,
)
from src.api.schemas.auth import User

# Bearer認証スキーム
security = HTTPBearer()

# APIキーヘッダー
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> User:
    """現在のユーザーを取得"""
    token = credentials.credentials

    # トークンをデコード
    token_data = jwt_handler.decode_token(token)

    if token_data is None:
        raise AuthenticationException("無効な認証トークンです")

    # TODO: 実際のデータベースからユーザーを取得
    # ここではモックユーザーを返す
    user = User(
        id=token_data.user_id or 1,
        username=token_data.username,
        email=f"{token_data.username}@example.com",
        full_name="Test User",
        is_active=True,
        created_at=datetime.utcnow()
    )

    if not user.is_active:
        raise AuthenticationException("無効なユーザーです")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """アクティブなユーザーを取得"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="アクティブでないユーザー"
        )
    return current_user


def require_scopes(required_scopes: List[str]):
    """スコープ要求デコレータ"""
    async def scope_checker(
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        token = credentials.credentials
        token_data = jwt_handler.decode_token(token)

        if token_data is None:
            raise AuthenticationException()

        # スコープチェック
        for scope in required_scopes:
            if scope not in token_data.scopes:
                raise AuthorizationException(
                    f"必要なスコープ '{scope}' がありません"
                )

        return token_data

    return scope_checker


async def get_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[str]:
    """APIキーを取得"""
    if api_key is None:
        return None

    # TODO: データベースからAPIキーを検証
    # ここでは簡易的な検証
    if not api_key.startswith("sk_"):
        raise AuthenticationException("無効なAPIキー形式です")

    return api_key


async def require_api_key(
    api_key: str = Depends(get_api_key)
) -> str:
    """APIキーを要求"""
    if api_key is None:
        raise AuthenticationException("APIキーが必要です")

    # TODO: データベースでAPIキーの有効性を確認
    # ここでは仮の検証
    if len(api_key) < 35:
        raise AuthenticationException("無効なAPIキーです")

    return api_key


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[User]:
    """オプショナルユーザー取得（認証不要エンドポイント用）"""
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials)
    except:
        return None


class RateLimitChecker:
    """レート制限チェッカー"""

    def __init__(self, requests: int = 100, window: int = 60):
        self.requests = requests
        self.window = window

    async def __call__(
        self,
        user: Optional[User] = Depends(get_optional_user),
        api_key: Optional[str] = Depends(get_api_key)
    ) -> bool:
        """レート制限チェック"""
        # TODO: Redisを使用した実際のレート制限実装
        # ここでは常にTrueを返す

        if not settings.rate_limit_enabled:
            return True

        # ユーザーまたはAPIキーで識別
        identifier = None
        if user:
            identifier = f"user:{user.id}"
        elif api_key:
            identifier = f"api_key:{api_key[:10]}"
        else:
            # 認証なしの場合はIPアドレスで制限（実装省略）
            identifier = "anonymous"

        # TODO: Redisでカウントチェック
        # if count > self.requests:
        #     raise RateLimitException(retry_after=60)

        return True


# 使用例のインスタンス
rate_limit_100 = RateLimitChecker(requests=100, window=60)
rate_limit_1000 = RateLimitChecker(requests=1000, window=3600)


from datetime import datetime  # インポート追加
