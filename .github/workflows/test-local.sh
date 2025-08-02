#!/bin/bash
# GitHub Actionsのワークフローをローカルでテストするスクリプト

echo "🧪 GitHub Actions ローカルテスト開始..."

# Python環境のセットアップ
echo "📦 Python環境のセットアップ..."
uv venv
source .venv/bin/activate

# 依存関係のインストール
echo "📥 依存関係のインストール..."
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt

# データベースのセットアップ（Docker Composeを使用）
echo "🗄️ テスト用データベースの起動..."
docker-compose up -d mysql

# データベースの起動を待つ
echo "⏳ データベースの起動を待機中..."
for i in {1..30}; do
  if mysqladmin ping -h localhost -u keiba_user -pkeiba_password --silent 2>/dev/null; then
    echo "✅ MySQLが起動しました"
    break
  fi
  echo "Waiting for MySQL... ($i/30)"
  sleep 2
done

# マイグレーションの実行
echo "🔄 マイグレーションの実行..."
DATABASE_URL="mysql+pymysql://keiba_user:keiba_password@localhost:3306/keiba_ai?charset=utf8mb4" uv run alembic upgrade head

# テストの実行
echo "🧪 テストの実行..."
DATABASE_URL="mysql+pymysql://keiba_user:keiba_password@localhost:3306/keiba_ai?charset=utf8mb4" uv run pytest tests/ -v --cov=src --cov-report=term

# Lintチェック
echo "🔍 Lintチェック..."
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# 型チェック
echo "🔍 型チェック..."
uv run mypy src/ --ignore-missing-imports || true

# クリーンアップ
echo "🧹 クリーンアップ..."
docker-compose down

echo "✅ ローカルテスト完了！"