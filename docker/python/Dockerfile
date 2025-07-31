# マルチステージビルド - ベースイメージ
ARG PYTHON_VERSION=3.10
FROM python:${PYTHON_VERSION}-slim as base

# 環境変数設定
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# システムパッケージのインストール
RUN apt-get update && apt-get install -y \
    # 基本ツール
    git \
    curl \
    wget \
    vim \
    # ビルドツール
    build-essential \
    # PostgreSQL開発ライブラリ
    libpq-dev \
    # 画像処理用
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # 日本語フォント
    fonts-noto-cjk \
    # タイムゾーン設定
    tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# タイムゾーン設定
ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# ユーザー作成（root以外での実行を推奨）
RUN useradd -m -u 1000 appuser

# 作業ディレクトリ設定
WORKDIR /app

# Pythonパッケージのインストール（開発用）
FROM base as dev

# requirements.txtをコピー
COPY requirements.txt requirements-dev.txt ./

# 依存パッケージのインストール
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements-dev.txt

# ソースコードのコピー
COPY --chown=appuser:appuser . .

# ユーザー切り替え
USER appuser

# デフォルトコマンド
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# 本番用イメージ
FROM base as production

# requirements.txtのみコピー
COPY requirements.txt ./

# 本番用パッケージのインストール
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    # キャッシュクリア
    rm -rf /root/.cache/pip

# ソースコードのコピー
COPY --chown=appuser:appuser ./src /app/src
COPY --chown=appuser:appuser ./configs /app/configs

# ユーザー切り替え
USER appuser

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# 本番用コマンド（gunicornを使用）
CMD ["gunicorn", "src.api.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]