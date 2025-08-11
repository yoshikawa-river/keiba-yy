"""
共通スキーマ定義
"""

from datetime import datetime
from typing import Any, Generic, Optional, TypeVar, Union

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseBase(BaseModel, Generic[T]):
    """基本レスポンス形式"""

    success: bool = Field(..., description="処理成功フラグ")
    data: Optional[T] = Field(None, description="レスポンスデータ")
    message: Optional[str] = Field(None, description="メッセージ")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="レスポンス生成時刻"
    )


class PaginationParams(BaseModel):
    """ページネーションパラメータ"""

    page: int = Field(default=1, ge=1, description="ページ番号")
    size: int = Field(default=20, ge=1, le=100, description="ページサイズ")

    @property
    def skip(self) -> int:
        """スキップ数を計算"""
        return (self.page - 1) * self.size


class PaginatedResponse(BaseModel, Generic[T]):
    """ページネーション付きレスポンス"""

    items: list[T] = Field(..., description="データリスト")
    total: int = Field(..., ge=0, description="総件数")
    page: int = Field(..., ge=1, description="現在のページ")
    size: int = Field(..., ge=1, description="ページサイズ")
    pages: int = Field(..., ge=0, description="総ページ数")
    has_next: bool = Field(..., description="次ページ存在フラグ")
    has_prev: bool = Field(..., description="前ページ存在フラグ")

    @classmethod
    def create(
        cls, items: list[T], total: int, page: int, size: int
    ) -> "PaginatedResponse[T]":
        """ページネーションレスポンスを作成"""
        pages = (total + size - 1) // size if size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        )


class ErrorDetail(BaseModel):
    """エラー詳細"""

    field: Optional[str] = Field(None, description="エラーフィールド")
    message: str = Field(..., description="エラーメッセージ")
    code: Optional[str] = Field(None, description="エラーコード")


class ErrorResponse(BaseModel):
    """エラーレスポンス"""

    success: bool = Field(default=False, description="処理成功フラグ")
    error: str = Field(..., description="エラー種別")
    message: str = Field(..., description="エラーメッセージ")
    details: Optional[list[ErrorDetail]] = Field(None, description="エラー詳細")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="エラー発生時刻"
    )
    request_id: Optional[str] = Field(None, description="リクエストID")


class HealthCheck(BaseModel):
    """ヘルスチェックレスポンス"""

    status: str = Field(..., description="サービスステータス")
    version: str = Field(..., description="APIバージョン")
    timestamp: datetime = Field(..., description="チェック時刻")
    uptime: int = Field(..., description="稼働時間（秒）")
    services: dict[str, bool] = Field(default_factory=dict, description="サービス状態")


class WebSocketMessage(BaseModel):
    """WebSocketメッセージ"""

    type: str = Field(..., description="メッセージタイプ")
    data: Any = Field(..., description="メッセージデータ")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="送信時刻")

    class Config:
        schema_extra = {
            "example": {
                "type": "prediction_update",
                "data": {
                    "race_id": "202312010101",
                    "status": "completed",
                    "result": {"win": [1, 3, 5]},
                },
                "timestamp": "2023-12-01T10:00:00",
            }
        }


class NotificationPreference(BaseModel):
    """通知設定"""

    email_enabled: bool = Field(default=True, description="メール通知")
    push_enabled: bool = Field(default=False, description="プッシュ通知")
    webhook_url: Optional[str] = Field(None, description="Webhook URL")
    notification_types: list[str] = Field(
        default_factory=lambda: ["prediction_complete", "error"],
        description="通知タイプ",
    )
