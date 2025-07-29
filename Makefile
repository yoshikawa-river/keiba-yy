# Makefile for 競馬予想AIシステム

# 変数定義
PYTHON := python3
DOCKER_COMPOSE := docker-compose
PROJECT_NAME := keiba-ai
SRC_DIR := src
TEST_DIR := tests
COVERAGE_DIR := htmlcov

# デフォルトのターゲット
.DEFAULT_GOAL := help

# カラー定義
COLOR_RESET   = \033[0m
COLOR_INFO    = \033[36m
COLOR_SUCCESS = \033[32m
COLOR_WARNING = \033[33m
COLOR_ERROR   = \033[31m

# ヘルプ表示
.PHONY: help
help: ## このヘルプメッセージを表示
	@echo "$(COLOR_INFO)競馬予想AIシステム - 開発用コマンド$(COLOR_RESET)"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "$(COLOR_SUCCESS)%-20s$(COLOR_RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(COLOR_INFO)使用例:$(COLOR_RESET)"
	@echo "  make setup        # 初回セットアップ"
	@echo "  make dev          # 開発環境起動"
	@echo "  make test         # テスト実行"

# =============================================================================
# セットアップ関連
# =============================================================================

.PHONY: setup
setup: ## 初回セットアップ（全体）
	@echo "$(COLOR_INFO)=== プロジェクトセットアップ開始 ===$(COLOR_RESET)"
	@make create-dirs
	@make install-hooks
	@make install-dev
	@make docker-build
	@echo "$(COLOR_SUCCESS)✓ セットアップ完了$(COLOR_RESET)"

.PHONY: create-dirs
create-dirs: ## プロジェクトディレクトリ作成
	@echo "$(COLOR_INFO)ディレクトリ構造を作成中...$(COLOR_RESET)"
	@bash scripts/setup/create_project_structure.sh

.PHONY: install-hooks
install-hooks: ## pre-commitフックのインストール
	@echo "$(COLOR_INFO)pre-commitフックをインストール中...$(COLOR_RESET)"
	@pre-commit install
	@pre-commit install --hook-type commit-msg

.PHONY: install-dev
install-dev: ## 開発用依存パッケージのインストール
	@echo "$(COLOR_INFO)開発用パッケージをインストール中...$(COLOR_RESET)"
	@$(PYTHON) -m pip install --upgrade pip
	@$(PYTHON) -m pip install -r requirements-dev.txt

.PHONY: clean-setup
clean-setup: ## セットアップのクリーンアップ
	@echo "$(COLOR_WARNING)セットアップをクリーンアップ中...$(COLOR_RESET)"
	@pre-commit uninstall
	@rm -rf venv/
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete

# =============================================================================
# Docker関連
# =============================================================================

.PHONY: docker-build
docker-build: ## Dockerイメージをビルド
	@echo "$(COLOR_INFO)Dockerイメージをビルド中...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) build

.PHONY: docker-build-no-cache
docker-build-no-cache: ## Dockerイメージをキャッシュなしでビルド
	@echo "$(COLOR_INFO)Dockerイメージをクリーンビルド中...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) build --no-cache

.PHONY: up
up: ## Docker環境を起動
	@echo "$(COLOR_INFO)Docker環境を起動中...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) up -d
	@echo "$(COLOR_SUCCESS)✓ サービスが起動しました$(COLOR_RESET)"
	@echo "  - Jupyter Lab: http://localhost:8888"
	@echo "  - Streamlit:   http://localhost:8501"
	@echo "  - MLflow:      http://localhost:5000"
	@echo "  - API:         http://localhost:8000"

.PHONY: down
down: ## Docker環境を停止
	@echo "$(COLOR_INFO)Docker環境を停止中...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) down

.PHONY: restart
restart: down up ## Docker環境を再起動

.PHONY: ps
ps: ## Dockerコンテナの状態を表示
	@$(DOCKER_COMPOSE) ps

.PHONY: logs
logs: ## Dockerログを表示（全サービス）
	@$(DOCKER_COMPOSE) logs -f

.PHONY: logs-app
logs-app: ## アプリケーションのログを表示
	@$(DOCKER_COMPOSE) logs -f app

.PHONY: shell
shell: ## Pythonコンテナのシェルに接続
	@$(DOCKER_COMPOSE) exec app bash

.PHONY: db-shell
db-shell: ## データベースのシェルに接続
	@$(DOCKER_COMPOSE) exec postgres psql -U keiba_user -d keiba_db

.PHONY: clean-docker
clean-docker: ## Dockerリソースをクリーンアップ
	@echo "$(COLOR_WARNING)Dockerリソースをクリーンアップ中...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) down -v
	@docker system prune -f

# =============================================================================
# 開発関連
# =============================================================================

.PHONY: dev
dev: ## 開発サーバーを起動（ローカル）
	@echo "$(COLOR_INFO)開発サーバーを起動中...$(COLOR_RESET)"
	@python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: jupyter
jupyter: ## Jupyter Labを起動
	@echo "$(COLOR_INFO)Jupyter Labを起動中...$(COLOR_RESET)"
	@open http://localhost:8888

.PHONY: streamlit
streamlit: ## Streamlitダッシュボードを起動
	@echo "$(COLOR_INFO)Streamlitを起動中...$(COLOR_RESET)"
	@open http://localhost:8501

.PHONY: mlflow
mlflow: ## MLflow UIを起動
	@echo "$(COLOR_INFO)MLflow UIを起動中...$(COLOR_RESET)"
	@open http://localhost:5000

# =============================================================================
# コード品質関連
# =============================================================================

.PHONY: format
format: ## コードをフォーマット（black + isort）
	@echo "$(COLOR_INFO)コードをフォーマット中...$(COLOR_RESET)"
	@black $(SRC_DIR) $(TEST_DIR)
	@isort $(SRC_DIR) $(TEST_DIR)

.PHONY: lint
lint: ## コードをリント（flake8 + mypy）
	@echo "$(COLOR_INFO)コードをリント中...$(COLOR_RESET)"
	@flake8 $(SRC_DIR) $(TEST_DIR)
	@mypy $(SRC_DIR)

.PHONY: check
check: format lint ## フォーマットとリントを実行

.PHONY: pre-commit
pre-commit: ## pre-commitを手動実行
	@pre-commit run --all-files

# =============================================================================
# テスト関連
# =============================================================================

.PHONY: test
test: ## テストを実行
	@echo "$(COLOR_INFO)テストを実行中...$(COLOR_RESET)"
	@pytest $(TEST_DIR) -v

.PHONY: test-cov
test-cov: ## カバレッジ付きでテストを実行
	@echo "$(COLOR_INFO)カバレッジ測定中...$(COLOR_RESET)"
	@pytest $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=html --cov-report=term

.PHONY: test-watch
test-watch: ## ファイル変更を監視してテストを自動実行
	@echo "$(COLOR_INFO)テスト監視モード...$(COLOR_RESET)"
	@ptw $(TEST_DIR) -- -v

.PHONY: open-cov
open-cov: ## カバレッジレポートを開く
	@open $(COVERAGE_DIR)/index.html

# =============================================================================
# データ関連
# =============================================================================

.PHONY: csv-import
csv-import: ## CSVファイルをインポート
	@echo "$(COLOR_INFO)CSVファイルをインポート中...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) exec app python scripts/data/import_csv.py

.PHONY: db-migrate
db-migrate: ## データベースマイグレーションを実行
	@echo "$(COLOR_INFO)マイグレーションを実行中...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) exec app alembic upgrade head

.PHONY: db-rollback
db-rollback: ## データベースを1つ前にロールバック
	@echo "$(COLOR_WARNING)データベースをロールバック中...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) exec app alembic downgrade -1

.PHONY: db-reset
db-reset: ## データベースをリセット
	@echo "$(COLOR_WARNING)データベースをリセット中...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) exec app alembic downgrade base
	@$(DOCKER_COMPOSE) exec app alembic upgrade head

# =============================================================================
# 機械学習関連
# =============================================================================

.PHONY: train
train: ## モデルの学習を実行
	@echo "$(COLOR_INFO)モデルを学習中...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) exec app python scripts/ml/train_model.py

.PHONY: predict
predict: ## 予測を実行
	@echo "$(COLOR_INFO)予測を実行中...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) exec app python scripts/ml/predict.py

.PHONY: evaluate
evaluate: ## モデルの評価を実行
	@echo "$(COLOR_INFO)モデルを評価中...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) exec app python scripts/ml/evaluate_model.py

# =============================================================================
# ドキュメント関連
# =============================================================================

.PHONY: docs
docs: ## ドキュメントを生成
	@echo "$(COLOR_INFO)ドキュメントを生成中...$(COLOR_RESET)"
	@cd docs && make html

.PHONY: docs-serve
docs-serve: ## ドキュメントサーバーを起動
	@echo "$(COLOR_INFO)ドキュメントサーバーを起動中...$(COLOR_RESET)"
	@cd docs && python -m http.server 8080

# =============================================================================
# バックアップ関連
# =============================================================================

.PHONY: backup
backup: ## データベースをバックアップ
	@echo "$(COLOR_INFO)データベースをバックアップ中...$(COLOR_RESET)"
	@mkdir -p backups
	@$(DOCKER_COMPOSE) exec postgres pg_dump -U keiba_user keiba_db > \
		backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(COLOR_SUCCESS)✓ バックアップ完了$(COLOR_RESET)"

.PHONY: restore
restore: ## 最新のバックアップから復元
	@echo "$(COLOR_WARNING)データベースを復元中...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) exec -T postgres psql -U keiba_user keiba_db < \
		$(shell ls -t backups/*.sql | head -1)
	@echo "$(COLOR_SUCCESS)✓ 復元完了$(COLOR_RESET)"

# =============================================================================
# その他
# =============================================================================

.PHONY: clean
clean: ## 一時ファイルをクリーンアップ
	@echo "$(COLOR_INFO)一時ファイルをクリーンアップ中...$(COLOR_RESET)"
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name ".DS_Store" -delete
	@rm -rf .pytest_cache
	@rm -rf .coverage
	@rm -rf $(COVERAGE_DIR)
	@rm -rf .mypy_cache

.PHONY: version
version: ## バージョン情報を表示
	@echo "$(COLOR_INFO)バージョン情報:$(COLOR_RESET)"
	@echo "  Python:         $(shell python --version)"
	@echo "  Docker:         $(shell docker --version)"
	@echo "  Docker Compose: $(shell docker-compose --version)"
	@echo "  Project:        $(PROJECT_NAME) v0.1.0"

.PHONY: check-deps
check-deps: ## 依存関係の更新をチェック
	@echo "$(COLOR_INFO)依存関係の更新をチェック中...$(COLOR_RESET)"
	@pip list --outdated

# Git関連のエイリアス
.PHONY: git-status
git-status: ## Git status
	@git status

.PHONY: git-pull
git-pull: ## Git pull
	@git pull origin develop

.PHONY: git-push
git-push: ## Git push
	@git push origin develop

# 開発フロー用の複合コマンド
.PHONY: dev-start
dev-start: up logs ## 開発環境を起動してログを表示

.PHONY: dev-stop
dev-stop: down clean ## 開発環境を停止してクリーンアップ

.PHONY: dev-restart
dev-restart: dev-stop dev-start ## 開発環境を完全に再起動

.PHONY: dev-check
dev-check: check test ## コード品質チェックとテストを実行

.PHONY: release-check
release-check: clean check test-cov docs ## リリース前の完全チェック