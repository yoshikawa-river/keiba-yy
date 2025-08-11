"""
カスタム例外クラス定義
"""

from typing import Any, Optional

from fastapi import HTTPException, status


class KeibaAPIException(HTTPException):
    """基本例外クラス"""

    def __init__(
        self, status_code: int, detail: str, headers: Optional[dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class AuthenticationException(KeibaAPIException):
    """認証エラー"""

    def __init__(self, detail: str = "認証に失敗しました"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationException(KeibaAPIException):
    """認可エラー"""

    def __init__(self, detail: str = "このリソースへのアクセス権限がありません"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ResourceNotFoundException(KeibaAPIException):
    """リソース未検出エラー"""

    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} (ID: {identifier}) が見つかりません",
        )


class ValidationException(KeibaAPIException):
    """バリデーションエラー"""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )


class RateLimitException(KeibaAPIException):
    """レート制限エラー"""

    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"レート制限を超えました。{retry_after}秒後に再試行してください",
            headers={"Retry-After": str(retry_after)},
        )


class PredictionException(KeibaAPIException):
    """予測処理エラー"""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"予測処理中にエラーが発生しました: {detail}",
        )


class WebSocketException(Exception):
    """WebSocket関連エラー"""

    def __init__(self, code: int, reason: str):
        self.code = code
        self.reason = reason
        super().__init__(f"WebSocket error {code}: {reason}")
