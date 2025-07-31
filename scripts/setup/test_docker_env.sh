#!/bin/bash
# test_docker_env.sh - Docker環境のテストスクリプト

set -e  # エラーで停止

# カラー定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🐳 Docker環境のテストを開始します..."

# Docker Desktopが起動しているか確認
echo -n "Docker Desktopの確認... "
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 起動しています${NC}"
else
    echo -e "${RED}✗ Docker Desktopが起動していません${NC}"
    echo "Docker Desktopを起動してから再度実行してください"
    exit 1
fi

# Docker Composeのバージョン確認
echo -n "Docker Composeの確認... "
if docker-compose --version > /dev/null 2>&1; then
    VERSION=$(docker-compose --version)
    echo -e "${GREEN}✓ $VERSION${NC}"
else
    echo -e "${RED}✗ Docker Composeがインストールされていません${NC}"
    exit 1
fi

# 必要なディレクトリの作成
echo "必要なディレクトリを作成中..."
mkdir -p volumes/csv_import
mkdir -p volumes/mlflow
mkdir -p logs
echo -e "${GREEN}✓ ディレクトリ作成完了${NC}"

# .envファイルの確認
echo -n ".envファイルの確認... "
if [ ! -f .env ]; then
    echo -e "${YELLOW}! .envファイルが見つかりません。作成します...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .envファイルを作成しました${NC}"
else
    echo -e "${GREEN}✓ 存在します${NC}"
fi

# Docker Composeの設定確認
echo -n "docker-compose.ymlの検証... "
if docker-compose config > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 正常です${NC}"
else
    echo -e "${RED}✗ 設定にエラーがあります${NC}"
    docker-compose config
    exit 1
fi

# Dockerイメージのビルド
echo ""
echo "📦 Dockerイメージをビルドします..."
if docker-compose build --no-cache; then
    echo -e "${GREEN}✓ ビルド成功${NC}"
else
    echo -e "${RED}✗ ビルド失敗${NC}"
    exit 1
fi

# サービスの起動
echo ""
echo "🚀 サービスを起動します..."
if docker-compose up -d; then
    echo -e "${GREEN}✓ 起動成功${NC}"
else
    echo -e "${RED}✗ 起動失敗${NC}"
    exit 1
fi

# サービスが正常に起動するまで待機
echo ""
echo "サービスの起動を待機中..."
sleep 10

# 各サービスのヘルスチェック
echo ""
echo "🏥 ヘルスチェックを実行中..."

# PostgreSQL
echo -n "PostgreSQL... "
if docker-compose exec -T postgres pg_isready -U keiba_user > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 正常${NC}"
else
    echo -e "${RED}✗ 接続できません${NC}"
fi

# Redis
echo -n "Redis... "
if docker-compose exec -T redis redis-cli ping | grep -q PONG; then
    echo -e "${GREEN}✓ 正常${NC}"
else
    echo -e "${RED}✗ 接続できません${NC}"
fi

# FastAPI
echo -n "FastAPI... "
if curl -s http://localhost:8000/health | grep -q healthy; then
    echo -e "${GREEN}✓ 正常${NC}"
else
    echo -e "${RED}✗ 接続できません${NC}"
fi

# Jupyter Lab
echo -n "Jupyter Lab... "
if curl -s http://localhost:8888/api | grep -q version; then
    echo -e "${GREEN}✓ 正常${NC}"
else
    echo -e "${RED}✗ 接続できません${NC}"
fi

# Streamlit
echo -n "Streamlit... "
if curl -s http://localhost:8501 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 正常${NC}"
else
    echo -e "${YELLOW}! 起動中の可能性があります${NC}"
fi

# MLflow
echo -n "MLflow... "
if curl -s http://localhost:5000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 正常${NC}"
else
    echo -e "${RED}✗ 接続できません${NC}"
fi

# サービスの状態表示
echo ""
echo "📊 サービスの状態:"
docker-compose ps

echo ""
echo "🎉 テスト完了！"
echo ""
echo "以下のURLでサービスにアクセスできます:"
echo "  - FastAPI:     http://localhost:8000"
echo "  - Jupyter Lab: http://localhost:8888 (Token: ${JUPYTER_TOKEN:-keiba_jupyter_token})"
echo "  - Streamlit:   http://localhost:8501"
echo "  - MLflow:      http://localhost:5000"
echo "  - Flower:      http://localhost:5555"
echo ""
echo "サービスを停止する場合: make down"