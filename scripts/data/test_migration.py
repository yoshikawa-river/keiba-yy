#!/usr/bin/env python
"""
マイグレーションテストスクリプト

Alembicマイグレーションの動作確認用
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from sqlalchemy import create_engine, text


def test_database_connection():
    """データベース接続テスト"""
    # 環境変数から接続情報を取得
    host = os.getenv("DATABASE_HOST", "mysql")
    port = os.getenv("DATABASE_PORT", "3306")
    user = os.getenv("DATABASE_USER", "keiba_user")
    password = os.getenv("DATABASE_PASSWORD", "keiba_password")
    database = os.getenv("DATABASE_NAME", "keiba_db")

    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"

    print("データベース接続テスト...")
    print(f"接続URL: mysql+pymysql://{user}:****@{host}:{port}/{database}")

    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ データベース接続成功")

            # 既存のテーブルを確認
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]
            print(f"\n既存のテーブル数: {len(tables)}")
            if tables:
                print("既存のテーブル:")
                for table in sorted(tables):
                    print(f"  - {table}")

        return engine
    except Exception as e:
        print(f"❌ データベース接続エラー: {e}")
        sys.exit(1)


def check_table_structure(engine):
    """テーブル構造の確認"""
    print("\n\nテーブル構造の確認...")

    with engine.connect() as conn:
        # 主要なテーブルの構造を確認
        tables_to_check = ["races", "horses", "race_entries", "race_results"]

        for table in tables_to_check:
            try:
                result = conn.execute(text(f"DESCRIBE {table}"))
                columns = list(result)
                print(f"\n📋 {table} テーブル:")
                print(f"  カラム数: {len(columns)}")
                print("  主要カラム:")
                for col in columns[:5]:  # 最初の5カラムのみ表示
                    print(f"    - {col[0]}: {col[1]}")
            except Exception:
                print(f"  ⚠️  {table} テーブルが見つかりません")


def main():
    """メイン処理"""
    print("=== マイグレーションテスト ===\n")

    # データベース接続テスト
    engine = test_database_connection()

    # テーブル構造確認
    check_table_structure(engine)

    print("\n\n=== テスト完了 ===")
    print("\n次のステップ:")
    print(
        '1. docker-compose exec app alembic revision --autogenerate -m "初期マイグレーション"'
    )
    print("2. docker-compose exec app alembic upgrade head")


if __name__ == "__main__":
    main()
