#!/bin/bash
# create_project_structure.sh

# プロジェクトルートディレクトリ名
PROJECT_NAME="keiba-ai"

# ディレクトリ作成関数
create_dir() {
    mkdir -p "$1"
    if [ "$2" = "python" ]; then
        touch "$1/__init__.py"
    fi
    if [ "$2" = "keep" ]; then
        touch "$1/.gitkeep"
    fi
}

# ルートレベルのディレクトリ
create_dir ".github/workflows"
create_dir "configs" "python"
create_dir "data/raw" "keep"
create_dir "data/processed" "keep"
create_dir "data/external" "keep"
create_dir "docker/python"
create_dir "docker/jupyter"
create_dir "docker/postgres"
create_dir "docs/api"
create_dir "docs/design"
create_dir "docs/guides"
create_dir "notebooks/exploratory" "keep"
create_dir "notebooks/modeling" "keep"
create_dir "notebooks/evaluation" "keep"
create_dir "outputs/models" "keep"
create_dir "outputs/predictions" "keep"
create_dir "outputs/reports" "keep"
create_dir "scripts/setup"
create_dir "scripts/data"
create_dir "scripts/deploy"

# srcディレクトリ
create_dir "src" "python"
create_dir "src/core" "python"
create_dir "src/data" "python"
create_dir "src/data/importers" "python"
create_dir "src/data/models" "python"
create_dir "src/data/repositories" "python"
create_dir "src/features" "python"
create_dir "src/features/extractors" "python"
create_dir "src/ml" "python"
create_dir "src/ml/models" "python"
create_dir "src/ml/trainers" "python"
create_dir "src/ml/predictors" "python"
create_dir "src/api" "python"
create_dir "src/api/routers" "python"
create_dir "src/api/schemas" "python"
create_dir "src/tasks" "python"
create_dir "src/utils" "python"

# streamlitディレクトリ
create_dir "streamlit"
create_dir "streamlit/pages"
create_dir "streamlit/components"

# testsディレクトリ
create_dir "tests" "python"
create_dir "tests/unit" "python"
create_dir "tests/integration" "python"
create_dir "tests/fixtures" "python"

# volumesディレクトリ
create_dir "volumes/csv_import" "keep"
create_dir "volumes/mlflow" "keep"

echo "プロジェクト構造の作成が完了しました。"