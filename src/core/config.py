"""
アプリケーション設定管理

環境変数と設定ファイルから設定を読み込み、
アプリケーション全体で使用する設定を管理する
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """アプリケーション設定"""

    # === 環境設定 ===
    APP_NAME: str = "keiba-ai"
    APP_ENV: str = Field(default="development", description="実行環境")
    DEBUG: bool = Field(default=True, description="デバッグモード")

    # === API設定 ===
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    API_TITLE: str = "競馬予想AI API"
    API_VERSION: str = "1.0.0"
    API_WORKERS: int = Field(default=1, description="APIワーカー数")

    # === データベース設定 ===
    DATABASE_HOST: str = Field(default="mysql", description="データベースホスト")
    DATABASE_PORT: int = Field(default=3306, description="データベースポート")
    DATABASE_NAME: str = Field(default="keiba_db", description="データベース名")
    DATABASE_USER: str = Field(default="keiba_user", description="データベースユーザー")
    DATABASE_PASSWORD: str = Field(default="keiba_password", description="データベースパスワード")
    DATABASE_POOL_SIZE: int = Field(default=10, description="コネクションプールサイズ")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, description="最大オーバーフロー数")
    DATABASE_POOL_PRE_PING: bool = Field(default=True, description="接続前のping確認")

    # === Redis設定 ===
    REDIS_HOST: str = Field(default="redis", description="Redisホスト")
    REDIS_PORT: int = Field(default=6379, description="Redisポート")
    REDIS_DB: int = Field(default=0, description="Redis DB番号")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redisパスワード")

    # === Celery設定 ===
    CELERY_BROKER_URL: str = Field(
        default="redis://redis:6379/0", description="Celeryブローカー URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://redis:6379/0", description="Celery結果バックエンド"
    )
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list = ["json"]
    CELERY_TIMEZONE: str = "Asia/Tokyo"
    CELERY_ENABLE_UTC: bool = True

    # === セキュリティ設定 ===
    SECRET_KEY: str = Field(
        default="your-secret-key-here",
        description="アプリケーションシークレットキー",
    )
    ALGORITHM: str = Field(default="HS256", description="JWT署名アルゴリズム")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="アクセストークン有効期限(分)")

    # === ログ設定 ===
    LOG_LEVEL: str = Field(default="INFO", description="ログレベル")
    LOG_FORMAT: str = Field(
        default="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        description="ログフォーマット",
    )
    LOG_FILE: Optional[str] = Field(default=None, description="ログファイルパス")

    # === MLflow設定 ===
    MLFLOW_TRACKING_URI: str = Field(
        default="http://mlflow:5000", description="MLflowトラッキングURI"
    )
    MLFLOW_EXPERIMENT_NAME: str = Field(
        default="keiba-prediction", description="MLflow実験名"
    )

    # === JRA-VAN設定 ===
    JRAVAN_USER_ID: Optional[str] = Field(default=None, description="JRA-VANユーザーID")
    JRAVAN_PASSWORD: Optional[str] = Field(default=None, description="JRA-VANパスワード")

    # === パス設定 ===
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Optional[Path] = Field(default=None, description="データディレクトリ")
    MODEL_DIR: Optional[Path] = Field(default=None, description="モデルディレクトリ")
    LOG_DIR: Optional[Path] = Field(default=None, description="ログディレクトリ")
    PREDICTION_DIR: Optional[Path] = Field(default=None, description="予測結果ディレクトリ")

    # === 機械学習設定 ===
    ML_RANDOM_SEED: int = Field(default=42, description="乱数シード")
    ML_TEST_SIZE: float = Field(default=0.2, description="テストデータの割合")
    ML_VALIDATION_SIZE: float = Field(default=0.1, description="検証データの割合")

    @field_validator("APP_ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        """環境名の検証"""
        allowed = ["development", "staging", "production", "test"]
        if v not in allowed:
            raise ValueError(f"APP_ENV must be one of {allowed}")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """ログレベルの検証"""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v

    @property
    def DATABASE_URL(self) -> str:
        """データベース接続URL"""
        return (
            f"mysql+pymysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def REDIS_URL(self) -> str:
        """Redis接続URL"""
        if self.REDIS_PASSWORD:
            return (
                f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:"
                f"{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def is_development(self) -> bool:
        """開発環境かどうか"""
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        """本番環境かどうか"""
        return self.APP_ENV == "production"

    @property
    def is_testing(self) -> bool:
        """テスト環境かどうか"""
        return self.APP_ENV == "test"

    def model_post_init(self, __context) -> None:
        """初期化後の処理"""
        # パス設定の初期化
        if self.DATA_DIR is None:
            self.DATA_DIR = self.BASE_DIR / "data"
        if self.MODEL_DIR is None:
            self.MODEL_DIR = self.BASE_DIR / "outputs" / "models"
        if self.LOG_DIR is None:
            self.LOG_DIR = self.BASE_DIR / "logs"
        if self.PREDICTION_DIR is None:
            self.PREDICTION_DIR = self.BASE_DIR / "outputs" / "predictions"

        # ディレクトリの作成
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.PREDICTION_DIR.mkdir(parents=True, exist_ok=True)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",  # 余分なフィールドを無視
        # "env_prefix": "KEIBA_",  # 環境変数のプレフィックス(オプション)
    }


@lru_cache
def get_settings() -> Settings:
    """
    設定のシングルトンインスタンスを取得

    環境変数APP_ENVに応じて適切な設定ファイルを読み込む
    """
    env = os.getenv("APP_ENV", "development")
    env_file = f".env.{env}" if env != "development" else ".env"

    # 環境別設定ファイルが存在する場合は使用
    if Path(env_file).exists():
        return Settings(_env_file=env_file)  # type: ignore

    return Settings()


# グローバル設定インスタンス
settings = get_settings()
