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
docker-compose up -d postgres

# データベースの起動を待つ
echo "⏳ データベースの起動を待機中..."
sleep 5

# マイグレーションの実行
echo "🔄 マイグレーションの実行..."
DATABASE_URL="postgresql://keiba_user:keiba_password@localhost:5432/keiba_ai" uv run alembic upgrade head

# テストの実行
echo "🧪 テストの実行..."
DATABASE_URL="postgresql://keiba_user:keiba_password@localhost:5432/keiba_ai" uv run pytest tests/ -v --cov=src --cov-report=term

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