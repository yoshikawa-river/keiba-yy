"""
ロギング設定

loguruを使用した統一的なロギング設定を提供
"""

import logging
import sys
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, Optional, Union

from loguru import logger

from src.core.config import settings


class LoggerManager:
    """ロガー管理クラス"""

    def __init__(self):
        """ロガーマネージャーの初期化"""
        self._configured = False

    def setup_logging(
        self,
        log_level: Optional[str] = None,
        log_file: Union[str, Path, None] = None,
        log_format: Optional[str] = None,
        serialize: bool = False,
        backtrace: bool = True,
        diagnose: bool = True,
    ) -> None:
        """
        ロギングの設定

        Args:
            log_level: ログレベル
            log_file: ログファイルパス
            log_format: ログフォーマット
            serialize: JSON形式で出力するか
            backtrace: スタックトレースを含めるか
            diagnose: 詳細な診断情報を含めるか
        """
        if self._configured:
            return

        # 既存のハンドラーを削除
        logger.remove()

        # デフォルト値の設定
        log_level = log_level or settings.LOG_LEVEL
        log_format = log_format or self._get_log_format()

        # コンソール出力の設定
        logger.add(
            sys.stderr,
            format=log_format,
            level=log_level,
            colorize=True,
            serialize=serialize,
            backtrace=backtrace,
            diagnose=diagnose,
        )

        # ファイル出力の設定
        if log_file or settings.LOG_FILE:
            log_path = Path(log_file or settings.LOG_FILE or "app.log")
            log_path.parent.mkdir(parents=True, exist_ok=True)

            logger.add(
                log_path,
                format=log_format,
                level=log_level,
                rotation="1 day",  # 1日ごとにローテーション
                retention="30 days",  # 30日間保持
                compression="zip",  # 古いログをzip圧縮
                serialize=serialize,
                backtrace=backtrace,
                diagnose=diagnose,
                encoding="utf-8",
            )

        # エラーログ専用ファイル(エラー以上のみ)
        if settings.LOG_DIR:
            error_log_path = settings.LOG_DIR / "error.log"
            logger.add(
                error_log_path,
                format=log_format,
                level="ERROR",
                rotation="1 week",
                retention="90 days",
                compression="zip",
                serialize=serialize,
                backtrace=True,  # エラーログは常にバックトレース含む
                diagnose=True,  # エラーログは常に診断情報含む
                encoding="utf-8",
            )

        # 標準ライブラリのloggingとの統合
        self._integrate_stdlib_logging()

        # SQLAlchemyのログレベル調整
        logging.getLogger("sqlalchemy.engine").setLevel(
            logging.INFO if settings.DEBUG else logging.WARNING
        )

        self._configured = True
        logger.info(f"Logging configured with level: {log_level}")

    def _get_log_format(self) -> str:
        """環境に応じたログフォーマットを取得"""
        if settings.is_production:
            # 本番環境: 構造化ログ
            return (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "{message}"
            )
        # 開発環境: 読みやすい形式
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    def _integrate_stdlib_logging(self) -> None:
        """標準ライブラリのloggingとloguruを統合"""

        class InterceptHandler(logging.Handler):
            """標準loggingのメッセージをloguruに転送"""

            def emit(self, record: logging.LogRecord) -> None:
                # loguruのレベルを取得
                try:
                    level = logger.level(record.levelname).name
                except ValueError:
                    level = str(record.levelno)

                # loguruでログ出力
                logger.opt(depth=6, exception=record.exc_info).log(
                    level, record.getMessage()
                )

        # 標準loggingの設定
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    def get_logger(self, name: str) -> "BoundLogger":
        """
        名前付きロガーを取得

        Args:
            name: ロガー名

        Returns:
            BoundLogger: 名前付きロガー
        """
        return BoundLogger(name)


# ロガーマネージャーのシングルトンインスタンス
logger_manager = LoggerManager()


def setup_logging(**kwargs) -> None:
    """ロギングの初期設定を実行"""
    logger_manager.setup_logging(**kwargs)


def log_execution_time(func: Callable) -> Callable:
    """
    関数の実行時間をログに記録するデコレーター

    使用例:
        @log_execution_time
        def heavy_process():
            time.sleep(1)
    """
    import time

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        logger.debug(f"Starting {func.__name__}")
        start = time.time()

        try:
            result = func(*args, **kwargs)
            logger.debug(f"Completed {func.__name__} in {time.time() - start:.2f}s")
            return result
        except Exception as e:
            logger.error(
                f"Error in {func.__name__} after {time.time() - start:.2f}s: {e}"
            )
            raise

    return wrapper


def log_async_execution_time(func: Callable) -> Callable:
    """
    非同期関数の実行時間をログに記録するデコレーター

    使用例:
        @log_async_execution_time
        async def async_heavy_process():
            await asyncio.sleep(1)
    """
    import time

    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        logger.debug(f"Starting async {func.__name__}")
        start = time.time()

        try:
            result = await func(*args, **kwargs)
            logger.debug(
                f"Completed async {func.__name__} in {time.time() - start:.2f}s"
            )
            return result
        except Exception as e:
            logger.error(
                f"Error in async {func.__name__} after {time.time() - start:.2f}s: {e}"
            )
            raise

    return wrapper


class BoundLogger:
    """名前付きロガーのラッパー"""

    def __init__(self, name: str):
        self.name = name
        self._logger = logger.bind(name=name)

    def debug(self, message: str, **kwargs) -> None:
        self._logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        self._logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self._logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        self._logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        self._logger.critical(message, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        self._logger.exception(message, **kwargs)


# デフォルトロガーのエクスポート
log = logger

# 初期設定の実行
setup_logging()
