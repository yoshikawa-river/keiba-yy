"""
API設定管理
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """アプリケーション設定"""

    # 基本設定
    app_name: str = "競馬予想AIシステム"
    app_version: str = "0.1.0"
    debug: bool = False

    # API設定
    api_v1_str: str = "/api/v1"
    api_port: int = 8000

    # セキュリティ設定
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS設定
    backend_cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8501"]

    # データベース設定（将来の接続用）
    database_url: Optional[str] = None

    # Redis設定（キャッシュ・レート制限用）
    redis_url: str = "redis://localhost:6379/0"

    # レート制限設定
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds

    # WebSocket設定
    websocket_heartbeat_interval: int = 30  # seconds
    websocket_max_connections: int = 100

    # ログ設定
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 予測モデル設定（モック用）
    model_confidence_threshold: float = 0.7
    max_batch_size: int = 100
    prediction_timeout: int = 30  # seconds

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """設定のシングルトンインスタンスを取得"""
    return Settings()


# グローバル設定インスタンス
settings = get_settings()
