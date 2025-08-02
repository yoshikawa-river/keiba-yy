"""
エラーハンドリング基盤

アプリケーション全体で使用する例外クラスと
エラーハンドリングのユーティリティを提供
"""
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.logging import logger


class KeibaAIException(Exception):
    """競馬予想AIシステムの基底例外クラス"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        カスタム例外の初期化

        Args:
            message: エラーメッセージ
            error_code: エラーコード
            status_code: HTTPステータスコード
            details: 詳細情報
        """
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """例外を辞書形式に変換"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# === ビジネスロジック例外 ===


class ValidationError(KeibaAIException):
    """バリデーションエラー"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class NotFoundError(KeibaAIException):
    """リソースが見つからないエラー"""

    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            error_code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "identifier": str(identifier)},
        )


class DuplicateError(KeibaAIException):
    """重複エラー"""

    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} already exists: {identifier}",
            error_code="DUPLICATE_ERROR",
            status_code=status.HTTP_409_CONFLICT,
            details={"resource": resource, "identifier": str(identifier)},
        )


class AuthenticationError(KeibaAIException):
    """認証エラー"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class AuthorizationError(KeibaAIException):
    """認可エラー"""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
        )


# === データアクセス例外 ===


class DatabaseError(KeibaAIException):
    """データベースエラー"""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        details = {}
        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__

        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class DataImportError(KeibaAIException):
    """データインポートエラー"""

    def __init__(self, message: str, file_path: Optional[str] = None):
        details = {}
        if file_path:
            details["file_path"] = file_path

        super().__init__(
            message=message,
            error_code="DATA_IMPORT_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class DataProcessingError(KeibaAIException):
    """データ処理エラー"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATA_PROCESSING_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class FeatureExtractionError(KeibaAIException):
    """特徴量抽出エラー"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="FEATURE_EXTRACTION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


# === 機械学習関連例外 ===


class ModelNotFoundError(KeibaAIException):
    """モデルが見つからないエラー"""

    def __init__(self, model_name: str, version: Optional[str] = None):
        message = f"Model not found: {model_name}"
        if version:
            message += f" (version: {version})"

        super().__init__(
            message=message,
            error_code="MODEL_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"model_name": model_name, "version": version},
        )


class PredictionError(KeibaAIException):
    """予測エラー"""

    def __init__(self, message: str, model_name: Optional[str] = None):
        details = {}
        if model_name:
            details["model_name"] = model_name

        super().__init__(
            message=message,
            error_code="PREDICTION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


# === 外部サービス例外 ===


class ExternalServiceError(KeibaAIException):
    """外部サービスエラー"""

    def __init__(self, service_name: str, message: str):
        super().__init__(
            message=f"{service_name}: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service": service_name},
        )


class JRAVANError(ExternalServiceError):
    """JRA-VANサービスエラー"""

    def __init__(self, message: str):
        super().__init__(service_name="JRA-VAN", message=message)


# === エラーハンドラー ===


async def keiba_exception_handler(
    request: Request, exc: KeibaAIException
) -> JSONResponse:
    """KeibaAIException用のエラーハンドラー"""
    logger.warning(
        f"{exc.error_code}: {exc.message}",
        extra={"details": exc.details, "path": request.url.path},
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """HTTPException用のエラーハンドラー"""
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={"path": request.url.path},
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": exc.detail,
            "details": {},
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """バリデーションエラー用のハンドラー"""
    logger.warning(
        "Request validation error",
        extra={"errors": exc.errors(), "path": request.url.path},
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Invalid request data",
            "details": {"errors": exc.errors()},
        },
    )


async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """SQLAlchemyエラー用のハンドラー"""
    if isinstance(exc, IntegrityError):
        logger.warning(
            f"Database integrity error: {exc}",
            extra={"path": request.url.path},
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "INTEGRITY_ERROR",
                "message": "Database integrity constraint violation",
                "details": {},
            },
        )

    logger.error(
        f"Database error: {exc}",
        extra={"path": request.url.path},
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "DATABASE_ERROR",
            "message": "Database operation failed",
            "details": {},
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """一般的な例外用のハンドラー"""
    logger.exception(
        "Unexpected error occurred",
        extra={"path": request.url.path},
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "details": {},
        },
    )


def register_exception_handlers(app):
    """
    FastAPIアプリケーションに例外ハンドラーを登録

    Args:
        app: FastAPIアプリケーションインスタンス
    """
    app.add_exception_handler(KeibaAIException, keiba_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)