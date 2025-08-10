"""
JWT認証ハンドラー
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.api.config import settings
from src.api.schemas.auth import TokenData

# パスワードハッシュ化コンテキスト
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class JWTHandler:
    """JWT認証処理クラス"""

    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        self.refresh_token_expire_days = settings.refresh_token_expire_days

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """パスワード検証"""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """パスワードハッシュ化"""
        return pwd_context.hash(password)

    def create_access_token(
        self,
        data: dict[str, Any],
        expires_delta: timedelta | None = None
    ) -> str:
        """アクセストークン作成"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({
            "exp": expire,
            "type": "access",
            "iat": datetime.utcnow()
        })

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self,
        data: dict[str, Any],
        expires_delta: timedelta | None = None
    ) -> str:
        """リフレッシュトークン作成"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        to_encode.update({
            "exp": expire,
            "type": "refresh",
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(32)  # JWT ID for refresh token tracking
        })

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> TokenData | None:
        """トークンデコード"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            user_id: int = payload.get("user_id")
            scopes: list = payload.get("scopes", [])

            if username is None:
                return None

            return TokenData(
                username=username,
                user_id=user_id,
                scopes=scopes
            )
        except JWTError:
            return None

    def verify_token(self, token: str, token_type: str = "access") -> dict[str, Any] | None:
        """トークン検証"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # トークンタイプ確認
            if payload.get("type") != token_type:
                return None

            return payload
        except JWTError:
            return None

    def generate_api_key(self) -> str:
        """APIキー生成"""
        # 32バイトのランダムトークンを生成
        raw_token = secrets.token_bytes(32)
        # SHA256でハッシュ化
        api_key = hashlib.sha256(raw_token).hexdigest()
        return f"sk_{api_key[:32]}"  # プレフィックスを付けて32文字に制限

    def hash_api_key(self, api_key: str) -> str:
        """APIキーのハッシュ化"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def verify_api_key(self, api_key: str, hashed_key: str) -> bool:
        """APIキー検証"""
        return self.hash_api_key(api_key) == hashed_key

# シングルトンインスタンス
jwt_handler = JWTHandler()
