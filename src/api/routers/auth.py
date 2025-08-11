"""
認証関連のAPIエンドポイント
"""

from datetime import datetime
from typing import Any, Dict, cast

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from src.api.auth.jwt_handler import jwt_handler
from src.api.config import settings
from src.api.dependencies.auth import get_current_user, simple_rate_limit_100
from src.api.exceptions.custom_exceptions import AuthenticationException
from src.api.schemas.auth import (
    APIKey,
    APIKeyCreate,
    LoginRequest,
    PasswordChangeRequest,
    RefreshTokenRequest,
    Token,
    User,
    UserCreate,
)
from src.api.schemas.common import ResponseBase

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={401: {"description": "認証エラー"}, 403: {"description": "権限エラー"}},
)

# モックユーザーデータベース（実際にはDBを使用）
mock_users: Dict[str, Dict[str, Any]] = {
    "testuser": {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "hashed_password": jwt_handler.get_password_hash("Test123!@#"),
        "is_active": True,
        "created_at": datetime.utcnow(),
    },
    "admin": {
        "id": 2,
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "Admin User",
        "hashed_password": jwt_handler.get_password_hash("Admin123!@#"),
        "is_active": True,
        "created_at": datetime.utcnow(),
    },
}


@router.post(
    "/register", response_model=ResponseBase[User], status_code=status.HTTP_201_CREATED
)
async def register(
    user_create: UserCreate, _: bool = Depends(simple_rate_limit_100)
) -> ResponseBase[User]:
    """
    新規ユーザー登録

    - **username**: ユーザー名（3-50文字）
    - **email**: メールアドレス
    - **password**: パスワード（8文字以上、大文字・小文字・数字・特殊文字を含む）
    """
    # ユーザー名の重複チェック
    if user_create.username in mock_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このユーザー名は既に使用されています",
        )

    # パスワードハッシュ化
    hashed_password = jwt_handler.get_password_hash(user_create.password)

    # ユーザー作成（実際はDBに保存）
    new_user = {
        "id": len(mock_users) + 1,
        "username": user_create.username,
        "email": user_create.email,
        "full_name": user_create.full_name or "",
        "hashed_password": hashed_password,
        "is_active": True,
        "created_at": datetime.utcnow(),
    }

    mock_users[user_create.username] = new_user

    # レスポンス用のユーザーオブジェクト
    user = User(
        id=cast(int, new_user["id"]),
        username=cast(str, new_user["username"]),
        email=cast(str, new_user["email"]),
        full_name=cast(str, new_user["full_name"]),
        is_active=cast(bool, new_user["is_active"]),
        created_at=cast(datetime, new_user["created_at"]),
    )

    return ResponseBase(success=True, data=user, message="ユーザー登録が完了しました")


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    _: bool = Depends(simple_rate_limit_100),
) -> Token:
    """
    ユーザーログイン（OAuth2互換）

    アクセストークンとリフレッシュトークンを返します。
    """
    # ユーザー認証
    user = mock_users.get(form_data.username)

    if not user:
        raise AuthenticationException("ユーザー名またはパスワードが正しくありません")

    if not jwt_handler.verify_password(form_data.password, cast(str, user["hashed_password"])):
        raise AuthenticationException("ユーザー名またはパスワードが正しくありません")

    if not cast(bool, user["is_active"]):
        raise AuthenticationException("このアカウントは無効化されています")

    # トークン作成
    access_token_data = {
        "sub": cast(str, user["username"]),
        "user_id": cast(int, user["id"]),
        "scopes": form_data.scopes,
    }

    access_token = jwt_handler.create_access_token(data=access_token_data)
    refresh_token = jwt_handler.create_refresh_token(data=access_token_data)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/login/custom", response_model=Token)
async def login_custom(
    login_request: LoginRequest, _: bool = Depends(simple_rate_limit_100)
) -> Token:
    """
    カスタムログインエンドポイント

    OAuth2形式ではなく、JSONボディでログイン情報を受け取ります。
    """
    # ユーザー認証
    user = mock_users.get(login_request.username)

    if not user:
        # メールアドレスでも検索
        for u in mock_users.values():
            if cast(str, u["email"]) == login_request.username:
                user = u
                break

    if not user:
        raise AuthenticationException("ユーザー名またはパスワードが正しくありません")

    if not jwt_handler.verify_password(login_request.password, cast(str, user["hashed_password"])):
        raise AuthenticationException("ユーザー名またはパスワードが正しくありません")

    # トークン作成
    access_token_data = {"sub": cast(str, user["username"]), "user_id": cast(int, user["id"]), "scopes": []}

    access_token = jwt_handler.create_access_token(data=access_token_data)
    refresh_token = jwt_handler.create_refresh_token(data=access_token_data)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_request: RefreshTokenRequest, _: bool = Depends(simple_rate_limit_100)
) -> Token:
    """
    トークンリフレッシュ

    リフレッシュトークンを使用して新しいアクセストークンを取得します。
    """
    # リフレッシュトークン検証
    payload = jwt_handler.verify_token(
        refresh_request.refresh_token, token_type="refresh"
    )

    if not payload:
        raise AuthenticationException("無効なリフレッシュトークンです")

    # 新しいトークン作成
    access_token_data = {
        "sub": payload.get("sub"),
        "user_id": payload.get("user_id"),
        "scopes": payload.get("scopes", []),
    }

    new_access_token = jwt_handler.create_access_token(data=access_token_data)
    new_refresh_token = jwt_handler.create_refresh_token(data=access_token_data)

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", response_model=ResponseBase[None])
async def logout(
    response: Response, current_user: User = Depends(get_current_user)
) -> ResponseBase[None]:
    """
    ログアウト

    トークンを無効化します（実際の実装ではRedisでブラックリスト管理）
    """
    # TODO: Redisにトークンをブラックリスト登録

    # クッキーをクリア（もし使用している場合）
    response.delete_cookie(key="access_token")

    return ResponseBase(success=True, data=None, message="ログアウトしました")


@router.get("/me", response_model=ResponseBase[User])
async def get_me(current_user: User = Depends(get_current_user)) -> ResponseBase[User]:
    """
    現在のユーザー情報取得
    """
    return ResponseBase(success=True, data=current_user, message=None)


@router.post("/change-password", response_model=ResponseBase[None])
async def change_password(
    password_change: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
) -> ResponseBase[None]:
    """
    パスワード変更
    """
    # 現在のパスワード確認
    user = mock_users.get(current_user.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ユーザーが見つかりません",
        )

    if not jwt_handler.verify_password(
        password_change.current_password, cast(str, user["hashed_password"])
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="現在のパスワードが正しくありません",
        )

    # 新しいパスワードをハッシュ化して保存
    user["hashed_password"] = jwt_handler.get_password_hash(
        password_change.new_password
    )

    return ResponseBase(success=True, data=None, message="パスワードを変更しました")


@router.post("/api-keys", response_model=ResponseBase[APIKey])
async def create_api_key(
    api_key_create: APIKeyCreate, current_user: User = Depends(get_current_user)
) -> ResponseBase[APIKey]:
    """
    APIキー作成
    """
    # APIキー生成
    api_key = jwt_handler.generate_api_key()

    # APIキー情報（実際はDBに保存）
    api_key_info = APIKey(
        id=1,
        name=api_key_create.name,
        key=api_key,  # 初回のみ平文で返す
        created_at=datetime.utcnow(),
        last_used_at=None,
        is_active=True,
    )

    # ハッシュ化してDBに保存（ここでは省略）
    # hashed_key = jwt_handler.hash_api_key(api_key)

    return ResponseBase(
        success=True,
        data=api_key_info,
        message="APIキーを作成しました。このキーは二度と表示されません。",
    )


@router.delete("/api-keys/{key_id}", response_model=ResponseBase[None])
async def delete_api_key(
    key_id: int, current_user: User = Depends(get_current_user)
) -> ResponseBase[None]:
    """
    APIキー削除
    """
    # TODO: データベースからAPIキーを削除

    return ResponseBase(success=True, data=None, message="APIキーを削除しました")
