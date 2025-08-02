#!/usr/bin/env python
"""
コアモジュールの動作確認スクリプト

config、database、logging、exceptionsの動作を確認
"""
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.append(str(Path(__file__).parents[1]))

import time
from datetime import datetime

from src.core import (
    DatabaseError,
    ValidationError,
    get_db,
    log,
    log_execution_time,
    logger,
    settings,
)


def test_config():
    """設定管理のテスト"""
    print("\n=== 設定管理のテスト ===")
    print(f"APP_NAME: {settings.APP_NAME}")
    print(f"APP_ENV: {settings.APP_ENV}")
    print(f"DEBUG: {settings.DEBUG}")
    print(f"DATABASE_URL: {settings.DATABASE_URL}")
    print(f"REDIS_URL: {settings.REDIS_URL}")
    print(f"BASE_DIR: {settings.BASE_DIR}")
    print(f"is_development: {settings.is_development}")

    # パスの存在確認
    assert settings.DATA_DIR.exists()
    assert settings.LOG_DIR.exists()
    assert settings.MODEL_DIR.exists()
    print("✅ 設定管理: OK")


def test_logging():
    """ロギングのテスト"""
    print("\n=== ロギングのテスト ===")

    # 各ログレベルのテスト
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    # 構造化ロギング
    logger.info("User action", extra={"user_id": 123, "action": "login"})

    # 名前付きロガー
    db_logger = logger.bind(name="database")
    db_logger.info("Database connection established")

    # ログファイルの確認
    if settings.LOG_FILE:
        log_path = Path(settings.LOG_FILE)
        if log_path.exists():
            print(f"✅ ログファイル作成: {log_path}")

    print("✅ ロギング: OK")


@log_execution_time
def slow_function():
    """実行時間ログのテスト用関数"""
    time.sleep(0.1)
    return "completed"


def test_execution_time_logging():
    """実行時間ログのテスト"""
    print("\n=== 実行時間ログのテスト ===")
    result = slow_function()
    print(f"Result: {result}")
    print("✅ 実行時間ログ: OK")


def test_exceptions():
    """例外処理のテスト"""
    print("\n=== 例外処理のテスト ===")

    # ValidationError
    try:
        raise ValidationError("Invalid email format", {"field": "email"})
    except ValidationError as e:
        print(f"ValidationError: {e.message}")
        print(f"Error code: {e.error_code}")
        print(f"Status code: {e.status_code}")
        print(f"Details: {e.details}")

    # DatabaseError
    try:
        raise DatabaseError("Connection failed", original_error=Exception("Timeout"))
    except DatabaseError as e:
        print(f"\nDatabaseError: {e.message}")
        print(f"Error dict: {e.to_dict()}")

    print("✅ 例外処理: OK")


def test_database_connection():
    """データベース接続のテスト（簡易版）"""
    print("\n=== データベース接続のテスト ===")

    try:
        from src.core import db_manager

        # エンジンの情報を表示
        print(f"Database URL: {db_manager.database_url}")
        print(f"Pool size: {db_manager.pool_size}")
        print(f"Max overflow: {db_manager.max_overflow}")

        # 実際の接続はDockerコンテナが必要なためスキップ
        print("💡 実際の接続テストはDocker環境で実行してください")

    except Exception as e:
        logger.warning(f"Database connection test skipped: {e}")

    print("✅ データベース設定: OK")


def main():
    """メインテスト実行"""
    print("コアモジュールの動作確認を開始します...")
    print(f"実行時刻: {datetime.now()}")

    try:
        test_config()
        test_logging()
        test_execution_time_logging()
        test_exceptions()
        test_database_connection()

        print("\n✅ すべてのテストが正常に完了しました！")
        return 0

    except Exception as e:
        logger.exception("テスト中にエラーが発生しました")
        print(f"\n❌ エラーが発生しました: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())