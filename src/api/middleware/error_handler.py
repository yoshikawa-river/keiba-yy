from typing import Union

"""
エラーハンドリングミドルウェア
"""

import logging
import traceback
import uuid

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.exceptions.custom_exceptions import KeibaAPIException
from src.api.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


async def http_exception_handler(
    request: Request, exc: Union[StarletteHTTPException, KeibaAPIException]
) -> JSONResponse:
    """HTTPException用のエラーハンドラー"""

    # リクエストIDの生成
    request_id = str(uuid.uuid4())

    # エラーログ出力
    logger.error(
        f"HTTP Exception - Request ID: {request_id}, "
        f"Path: {request.url.path}, "
        f"Status: {exc.status_code}, "
        f"Detail: {exc.detail}"
    )

    # エラーレスポンスの作成
    error_response = ErrorResponse(
        error=f"HTTP_{exc.status_code}", message=str(exc.detail), request_id=request_id
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode="json"),
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """バリデーションエラー用のハンドラー"""

    request_id = str(uuid.uuid4())

    # エラー詳細を抽出
    errors = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"][1:])  # bodyを除外
        errors.append(
            ErrorDetail(
                field=field_path if field_path else None,
                message=error["msg"],
                code=error["type"],
            )
        )

    # エラーログ出力
    logger.warning(
        f"Validation Error - Request ID: {request_id}, "
        f"Path: {request.url.path}, "
        f"Errors: {len(errors)}"
    )

    # エラーレスポンスの作成
    error_response = ErrorResponse(
        error="VALIDATION_ERROR",
        message="入力データの検証に失敗しました",
        details=errors,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(mode="json"),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """一般的な例外用のハンドラー"""

    request_id = str(uuid.uuid4())

    # スタックトレースを取得
    tb = traceback.format_exc()

    # エラーログ出力（スタックトレース含む）
    logger.error(
        f"Unhandled Exception - Request ID: {request_id}, "
        f"Path: {request.url.path}, "
        f"Exception: {type(exc).__name__}, "
        f"Message: {exc!s}\n"
        f"Traceback:\n{tb}"
    )

    # 本番環境では詳細なエラー情報を隠す
    error_response = ErrorResponse(
        error="INTERNAL_SERVER_ERROR",
        message="サーバー内部でエラーが発生しました",
        request_id=request_id,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(mode="json"),
    )
