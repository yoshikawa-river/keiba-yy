#!/bin/bash
# init_git.sh

# Gitリポジトリの初期化
git init

# 初期ブランチ名を main に設定
git config init.defaultBranch main

# ユーザー情報の設定（ローカル）
git config user.name "Your Name"
git config user.email "your.email@example.com"

# 初回コミット
git add .
git commit -m "Initial commit: プロジェクト基本構造"

# developブランチの作成
git checkout -b develop