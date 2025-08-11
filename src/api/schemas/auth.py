import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

"""
認証関連のスキーマ定義
"""


class UserBase(BaseModel):
    """ユーザー基本情報"""

    username: str = Field(..., min_length=3, max_length=50, description="ユーザー名")
    email: EmailStr = Field(..., description="メールアドレス")
    full_name: Optional[str] = Field(None, max_length=100, description="フルネーム")
    is_active: bool = Field(default=True, description="アクティブフラグ")


class UserCreate(UserBase):
    """ユーザー作成用スキーマ"""

    password: str = Field(..., min_length=8, max_length=100, description="パスワード")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """パスワードの強度チェック"""
        if not re.search(r"[A-Z]", v):
            raise ValueError("パスワードには大文字を含める必要があります")
        if not re.search(r"[a-z]", v):
            raise ValueError("パスワードには小文字を含める必要があります")
        if not re.search(r"\d", v):
            raise ValueError("パスワードには数字を含める必要があります")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("パスワードには特殊文字を含める必要があります")
        return v


class UserInDB(UserBase):
    """データベース内のユーザー情報"""

    id: int
    hashed_password: str
    created_at: datetime
    updated_at: datetime


class User(UserBase):
    """ユーザー情報（レスポンス用）"""

    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """認証トークン"""

    access_token: str = Field(..., description="アクセストークン")
    refresh_token: Optional[str] = Field(None, description="リフレッシュトークン")
    token_type: str = Field(default="bearer", description="トークンタイプ")
    expires_in: int = Field(..., description="有効期限（秒）")


class TokenData(BaseModel):
    """トークンデータ"""

    username: Optional[str] = None
    user_id: Optional[int] = None
    scopes: list[str] = []


class LoginRequest(BaseModel):
    """ログインリクエスト"""

    username: str = Field(..., description="ユーザー名またはメールアドレス")
    password: str = Field(..., description="パスワード")


class RefreshTokenRequest(BaseModel):
    """リフレッシュトークンリクエスト"""

    refresh_token: str = Field(..., description="リフレッシュトークン")


class PasswordChangeRequest(BaseModel):
    """パスワード変更リクエスト"""

    current_password: str = Field(..., description="現在のパスワード")
    new_password: str = Field(..., min_length=8, description="新しいパスワード")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v, info):
        """新しいパスワードの検証"""
        if (
            hasattr(info, "data")
            and info.data
            and "current_password" in info.data
            and v == info.data["current_password"]
        ):
            raise ValueError("新しいパスワードは現在のパスワードと異なる必要があります")
        # パスワード強度チェック（UserCreateと同じロジック）
        if not re.search(r"[A-Z]", v):
            raise ValueError("パスワードには大文字を含める必要があります")
        if not re.search(r"[a-z]", v):
            raise ValueError("パスワードには小文字を含める必要があります")
        if not re.search(r"\d", v):
            raise ValueError("パスワードには数字を含める必要があります")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("パスワードには特殊文字を含める必要があります")
        return v


class APIKey(BaseModel):
    """APIキー情報"""

    id: int
    name: str = Field(..., max_length=100, description="APIキー名")
    key: str = Field(..., description="APIキー")
    created_at: datetime
    last_used_at: Optional[datetime] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class APIKeyCreate(BaseModel):
    """APIキー作成リクエスト"""

    name: str = Field(..., max_length=100, description="APIキー名")
    expires_in_days: Optional[int] = Field(
        None, ge=1, le=365, description="有効期限（日数）"
    )
