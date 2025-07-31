# Jupyter Lab用Dockerfile
ARG PYTHON_VERSION=3.10
FROM python:${PYTHON_VERSION}-slim

# 環境変数設定
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    JUPYTER_ENABLE_LAB=yes

# システムパッケージのインストール
RUN apt-get update && apt-get install -y \
    # 基本ツール
    git \
    curl \
    wget \
    vim \
    # ビルドツール
    build-essential \
    # MySQL開発ライブラリ
    default-libmysqlclient-dev \
    pkg-config \
    # 画像処理・グラフ描画用
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgraphviz-dev \
    graphviz \
    # 日本語フォント
    fonts-noto-cjk \
    fonts-ipafont \
    # LaTeX（オプション：PDFエクスポート用）
    # texlive-xetex \
    # texlive-fonts-recommended \
    # texlive-plain-generic \
    # タイムゾーン設定
    tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# タイムゾーン設定
ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 作業ディレクトリ設定
WORKDIR /app

# requirements.txtをコピー
COPY requirements.txt requirements-dev.txt ./

# Jupyter関連パッケージの追加インストール
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install -r requirements-dev.txt && \
    pip install \
        jupyterlab==4.0.9 \
        jupyterlab-lsp==5.0.1 \
        jupyter-lsp-python==2.2.1 \
        jupyterlab-git==0.50.0 \
        jupyterlab-code-formatter==2.2.1 \
        jupyter-resource-usage==1.0.1 \
        ipywidgets==8.1.1 \
        nbdime==4.0.1 \
        jupyterlab_execute_time==3.1.1 \
        jupyterlab-drawio==0.9.0 \
        jupyterlab_vim==4.1.0 \
        aquirdturtle_collapsible_headings==3.1.0 \
        jupyterlab-spellchecker==0.8.4

# JupyterLab拡張機能の有効化
RUN jupyter labextension disable "@jupyterlab/apputils-extension:announcements"

# Jupyter設定ディレクトリ作成
RUN mkdir -p /root/.jupyter

# Jupyter設定ファイル作成
RUN echo "c.NotebookApp.token = ''" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.password = ''" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.allow_root = True" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.ip = '0.0.0.0'" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.port = 8888" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.notebook_dir = '/app/notebooks'" >> /root/.jupyter/jupyter_notebook_config.py

# IPythonの設定（自動リロード有効化）
RUN mkdir -p /root/.ipython/profile_default && \
    echo "c.InteractiveShellApp.extensions = ['autoreload']" >> /root/.ipython/profile_default/ipython_config.py && \
    echo "c.InteractiveShellApp.exec_lines = ['%autoreload 2']" >> /root/.ipython/profile_default/ipython_config.py

# ノートブック用ディレクトリ作成
RUN mkdir -p /app/notebooks

# ポート公開
EXPOSE 8888

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8888/api || exit 1

# デフォルトコマンド
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]