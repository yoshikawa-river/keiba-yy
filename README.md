# 競馬予想AIシステム

[![CI](https://github.com/yoshikawa-river/keiba-yy/actions/workflows/ci.yml/badge.svg)](https://github.com/yoshikawa-river/keiba-yy/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/yoshikawa-river/keiba-yy/branch/main/graph/badge.svg)](https://codecov.io/gh/yoshikawa-river/keiba-yy)

JRA-VAN DataLabのデータを活用した個人用競馬予想AIシステム

## 概要

このプロジェクトは、機械学習を用いて競馬レースの予測を行うシステムです。
JRA-VAN DataLabから取得したデータを基に、LightGBMやXGBoostなどの
アルゴリズムを使用して予測モデルを構築します。

## 主な機能

- JRA-VANデータのインポートと管理
- 特徴量エンジニアリング
- 複数の機械学習モデルによる予測
- 予測結果の可視化とダッシュボード
- バックテストによる性能評価

## 技術スタック

- **言語**: Python 3.10+
- **フレームワーク**: FastAPI, Streamlit
- **機械学習**: LightGBM, XGBoost, scikit-learn
- **データベース**: PostgreSQL, Redis
- **コンテナ**: Docker, Docker Compose
- **実験管理**: MLflow

## セットアップ

### 前提条件

- Docker Desktop for Mac
- Git
- Make
- JRA-VAN DataLab契約

### インストール手順

1. リポジトリのクローン
```bash
git clone [repository-url]
cd keiba-ai
```

2. 環境変数の設定
```bash
cp .env.example .env
# .envファイルを編集
```

3. Docker環境の起動
```bash
make setup
make build
make up
```

4. データのインポート
```bash
# CSVファイルを volumes/csv_import/ に配置後
make csv-import
```

## 使用方法

### 予測の実行
```bash
make predict
```

### ダッシュボードの表示
```bash
make streamlit
# ブラウザで http://localhost:8501 にアクセス
```

### Jupyter Labでの分析
```bash
make jupyter
# ブラウザで http://localhost:8888 にアクセス
```

## プロジェクト構成

```
.
├── docker/              # Dockerファイル
├── src/                 # ソースコード
│   ├── data/           # データ層
│   ├── features/       # 特徴量エンジニアリング
│   ├── ml/             # 機械学習モデル
│   └── api/            # API
├── notebooks/          # Jupyter Notebook
├── tests/              # テストコード
├── configs/            # 設定ファイル
└── docs/               # ドキュメント
```

## 開発

### コーディング規約

- PEP 8準拠
- Black/flake8によるフォーマット
- pre-commitフックの使用

### テスト
```bash
make test
```

### ドキュメント生成
```bash
make docs
```

## ライセンス

このプロジェクトは個人利用を目的としています。
JRA-VANデータの利用にはJRA-VAN利用規約が適用されます。

## 注意事項

- このシステムは参考情報の提供を目的としており、投資判断は自己責任で行ってください
- JRA-VANデータの商用利用は禁止されています
- 予測結果の正確性は保証されません

## 作者

[Your Name]

## 更新履歴

- 2025-07-29: 初版作成
