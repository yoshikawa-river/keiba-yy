.PHONY: help build up down restart docker_up docker_down docker_restart docker_quick_up docker_fast_up docker_fast_restart docker_status docker_benchmark docker_profile docker_logs_startup docker_up_core docker_up_api docker_up_analytics logs shell db-shell jupyter test lint format format-check setup-hooks clean

# デフォルトターゲット
.DEFAULT_GOAL := help

# ヘルプ
help: ## ヘルプを表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# 環境構築
setup: ## 初期セットアップ
	@echo "Setting up the project..."
	@cp .env.example .env 2>/dev/null || echo ".env already exists"
	@mkdir -p volumes/csv_import volumes/mlflow volumes/mysql_data logs outputs/models outputs/predictions outputs/reports
	@echo "Setup completed!"

# Docker操作
build: ## Dockerイメージをビルド
	docker compose build

up: ## コンテナを起動
	docker compose up -d

down: ## コンテナを停止
	docker compose down

restart: ## コンテナを再起動
	docker compose restart

# Docker管理（高速版）
docker_up: ## コンテナを高速起動（キャッシュ活用）
	@echo "🚀 Starting containers with optimized settings..."
	docker compose up -d --no-build
	@echo "✅ Containers started successfully!"

docker_down: ## コンテナを完全停止
	@echo "⏹️  Stopping all containers..."
	docker compose down
	@echo "✅ All containers stopped!"

docker_restart: ## コンテナを高速再起動
	@echo "🔄 Restarting containers..."
	$(MAKE) docker_down
	$(MAKE) docker_up
	@echo "✅ Containers restarted successfully!"

# Docker高速操作
docker_quick_up: ## 超高速起動（ヘルスチェックスキップ）
	@echo "⚡ Quick starting containers..."
	docker compose up -d --no-build --no-deps
	@echo "✅ Quick start completed!"

docker_fast_up: ## 高速起動（最適化設定使用）
	@echo "🚀 Starting containers with fast configuration..."
	docker compose -f docker-compose.yml -f docker-compose.fast.yml up -d --no-build
	@echo "✅ Fast start completed!"

docker_fast_restart: ## 高速再起動
	@echo "🔄 Fast restarting containers..."
	$(MAKE) docker_down
	$(MAKE) docker_fast_up
	@echo "✅ Fast restart completed!"

docker_status: ## コンテナ状態を確認
	@echo "📊 Container Status:"
	docker compose ps

docker_benchmark: ## 起動時間を測定
	@echo "⏱️  Benchmarking startup time..."
	@echo "Normal startup:"
	@time $(MAKE) docker_down && $(MAKE) docker_up
	@sleep 5
	@echo "Fast startup:"
	@time $(MAKE) docker_down && $(MAKE) docker_fast_up

docker_profile: ## 起動プロセスを分析
	@echo "🔍 Profiling container startup process..."
	@echo "Starting containers and monitoring startup..."
	docker compose -f docker-compose.yml -f docker-compose.fast.yml up -d --no-build
	@echo "Waiting for containers to stabilize..."
	@for i in {1..30}; do \
		echo "Check $$i/30:"; \
		docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"; \
		echo "---"; \
		sleep 2; \
		if [ "$$(docker compose ps --filter status=running | wc -l)" -ge 8 ]; then \
			echo "✅ All containers are running!"; \
			break; \
		fi; \
	done

docker_logs_startup: ## 起動時のログを確認
	@echo "📋 Showing startup logs for all services..."
	docker compose logs --tail=20 mysql redis app celery mlflow jupyter streamlit flower

# サービス別操作
docker_up_core: ## コアサービスのみ起動（MySQL, Redis）
	@echo "🗄️ Starting core services..."
	docker compose up -d mysql redis
	@echo "✅ Core services started!"

docker_up_api: ## APIサービス起動（App, Celery, Flower）
	@echo "🔧 Starting API services..."
	$(MAKE) docker_up_core
	docker compose up -d app celery flower
	@echo "✅ API services started!"

docker_up_analytics: ## 分析環境起動（Jupyter, MLflow, Streamlit）
	@echo "📊 Starting analytics services..."
	$(MAKE) docker_up_core
	docker compose up -d jupyter mlflow streamlit
	@echo "✅ Analytics services started!"

logs: ## ログを表示（全サービス）
	docker compose logs -f

logs-app: ## アプリケーションのログを表示
	docker compose logs -f app

logs-db: ## データベースのログを表示
	docker compose logs -f mysql

ps: ## コンテナの状態を表示
	docker compose ps

# コンテナ内操作
shell: ## アプリケーションコンテナにアクセス
	docker compose exec app bash

db-shell: ## MySQLコンテナにアクセス
	docker compose exec mysql mysql -u${DATABASE_USER:-keiba_user} -p${DATABASE_PASSWORD:-keiba_password} ${DATABASE_NAME:-keiba_db}

jupyter: ## Jupyter Labを起動
	docker compose up -d jupyter
	@echo "Jupyter Lab is running at http://localhost:8888"

streamlit: ## Streamlitを起動
	docker compose up -d streamlit
	@echo "Streamlit is running at http://localhost:8501"

mlflow: ## MLflowを起動
	docker compose up -d mlflow
	@echo "MLflow is running at http://localhost:5000"

# 開発ツール
test: ## テストを実行
	docker compose exec app pytest tests/ -v

test-cov: ## カバレッジ付きでテストを実行
	docker compose exec app pytest tests/ -v --cov=src --cov-report=html

lint: ## コードをチェック
	docker compose exec app flake8 src/
	docker compose exec app mypy src/

format: ## コードをフォーマット
	docker compose exec app black src/
	docker compose exec app isort src/

format-check: ## フォーマットをチェック（変更なし）
	docker compose exec app black --check src/
	docker compose exec app isort --check-only src/

setup-hooks: ## Git hooksをセットアップ
	@echo "Setting up Git hooks..."
	@mkdir -p .githooks
	git config core.hooksPath .githooks
	@echo "✅ Git hooks configured to use .githooks directory"
	@echo "💡 Pre-push hook will automatically format code and run linting"

# データベース操作
db-migrate: ## データベースマイグレーションを実行
	docker compose exec app alembic upgrade head

db-rollback: ## データベースマイグレーションをロールバック
	docker compose exec app alembic downgrade -1

db-reset: ## データベースをリセット（注意！）
	docker compose exec mysql mysql -u root -p${DATABASE_ROOT_PASSWORD:-root_password} -e "DROP DATABASE IF EXISTS ${DATABASE_NAME:-keiba_db}; CREATE DATABASE ${DATABASE_NAME:-keiba_db};"
	docker compose exec mysql mysql -u root -p${DATABASE_ROOT_PASSWORD:-root_password} ${DATABASE_NAME:-keiba_db} < docker/mysql/init.sql

# データ処理
csv-import: ## CSVファイルをインポート
	docker compose exec app python -m src.data.importers.csv_importer

train: ## モデルを学習
	docker compose exec app python -m src.ml.trainers.train_model

predict: ## 予測を実行
	docker compose exec app python -m src.ml.predictors.predict

# バッチジョブ
celery-worker: ## Celeryワーカーを起動
	docker compose up -d celery

celery-flower: ## Flower（Celery監視）を起動
	docker compose up -d flower
	@echo "Flower is running at http://localhost:5555"

# クリーンアップ
clean: ## 不要なファイルを削除
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .mypy_cache/

clean-all: clean ## すべてのDockerリソースをクリーンアップ（注意！）
	docker compose down -v
	docker system prune -af

# バックアップ
backup: ## データベースをバックアップ
	@mkdir -p backups
	docker compose exec mysql mysqldump -u${DATABASE_USER:-keiba_user} -p${DATABASE_PASSWORD:-keiba_password} ${DATABASE_NAME:-keiba_db} > backups/keiba_db_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup completed: backups/keiba_db_$(shell date +%Y%m%d_%H%M%S).sql"

restore: ## データベースをリストア（BACKUP_FILE=backups/xxx.sql）
	@if [ -z "$(BACKUP_FILE)" ]; then echo "Usage: make restore BACKUP_FILE=backups/xxx.sql"; exit 1; fi
	docker compose exec -T mysql mysql -u${DATABASE_USER:-keiba_user} -p${DATABASE_PASSWORD:-keiba_password} ${DATABASE_NAME:-keiba_db} < $(BACKUP_FILE)
	@echo "Restore completed from: $(BACKUP_FILE)"

# EvryDB2 Connection Test
test-connection: ## EvryDB2接続テストを実行
	docker compose exec app python scripts/test_evrydb2_connection.py

test-external-connection: ## 外部からの接続テスト（ホストマシンから実行）
	python scripts/test_evrydb2_connection.py