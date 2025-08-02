#!/bin/bash
set -euo pipefail

###### 使用方法 ######
# ./worktree.sh <branchName> # 指定した名前のブランチに対応するworktreeに移動
# ./worktree.sh -b <branchName> # 指定した名前のブランチに対応するworktreeディレクトリを作成し移動
# ./worktree.sh -d <branchName> # 指定した名前のブランチに対応するworktreeディレクトリを削除
# ./worktree.sh -l # 既存のworktreeディレクトリ一覧を表示
# ./worktree.sh -p <pr_number> # 指定したPRのブランチをチェックアウトしてworktree作成
# ./worktree.sh root # メインリポジトリ（メインディレクトリ）に移動
#####################

# 現在のGitリポジトリのルートディレクトリを取得
CURRENT_REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
CURRENT_REPO_NAME=$(basename "$CURRENT_REPO_ROOT" 2>/dev/null || echo "")

BASE_BRANCH=main
# スクリプトのディレクトリ（絶対パスで取得）
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
# メインリポジトリのルートを特定（worktreeの場合も対応）
# git worktree list の最初の行（メインworktree）からパスを取得
MAIN_REPO_ROOT=$(git worktree list | head -n 1 | awk '{print $1}')
MAIN_REPO_NAME=$(basename "$MAIN_REPO_ROOT")

# worktreeスクリプトの絶対パスを設定（どのディレクトリからでも使用可能にする）
WORKTREE_SCRIPT_PATH="${MAIN_REPO_ROOT}/scripts/git_worktree/worktree.sh"

# リポジトリの親ディレクトリ（メインリポジトリベース）
PARENT_DIR=$(dirname "$MAIN_REPO_ROOT")

# worktree ディレクトリかどうかを判定する
if [ "$(git rev-parse --git-dir)" = ".git" ]; then
  IS_WORKTREE=false
  BASE_REPO_NAME="${CURRENT_REPO_NAME}"
else
  IS_WORKTREE=true
  # worktreeの場合はメインリポジトリ名を使用
  BASE_REPO_NAME="${MAIN_REPO_NAME}"
fi

# 1. 現在のリポジトリがGitリポジトリであるかをチェック。Git リポジトリでなければ実行終了
if [ -z "$CURRENT_REPO_ROOT" ]; then
  echo "エラー: Gitリポジトリではありません。"
  exit 1
fi

# サブコマンドの処理
case "${1:-}" in
  "-l")
    # リスト表示モード
    echo "=== 既存のworktreeディレクトリ一覧 ==="
    echo
    
    # Git worktreeの一覧を表示
    echo "【Git worktree一覧】"
    git worktree list
    echo
    
    # 親ディレクトリ内の関連ディレクトリを検索
    echo "【関連ディレクトリ一覧】"
    echo "現在のリポジトリ: ${CURRENT_REPO_NAME}"
    echo "ベースリポジトリ: ${BASE_REPO_NAME}"
    echo
    
    # {branchName}_{repoName} 形式のディレクトリを検索
    FOUND_DIRS=false
    for dir in "${PARENT_DIR}"/*_"${BASE_REPO_NAME}"; do
      if [ -d "$dir" ] && [ "$dir" != "${CURRENT_REPO_ROOT}" ]; then
        if [ "$FOUND_DIRS" = false ]; then
          echo "ブランチ用worktreeディレクトリ:"
          FOUND_DIRS=true
        fi
        BRANCH_NAME=$(basename "$dir" | sed "s/_${BASE_REPO_NAME}$//")
        echo "  - $BRANCH_NAME ($(basename "$dir"))"
      fi
    done
    
    # pr-{number}_{repoName} 形式のディレクトリを検索
    FOUND_PR_DIRS=false
    for dir in "${PARENT_DIR}"/pr-*_"${BASE_REPO_NAME}"; do
      if [ -d "$dir" ]; then
        if [ "$FOUND_PR_DIRS" = false ]; then
          echo "PR用worktreeディレクトリ:"
          FOUND_PR_DIRS=true
        fi
        PR_INFO=$(basename "$dir" | sed "s/pr-\([0-9]*\)_${BASE_REPO_NAME}$/\1/")
        echo "  - PR #$PR_INFO ($(basename "$dir"))"
      fi
    done
    exit 0
    ;;
  "-p")
    # PRモード
    PR_NUMBER="$2"
    
    if [ -z "$PR_NUMBER" ]; then
      echo "Error: PR番号を指定してください。"
      echo "使用方法: ./worktree.sh -p <pr_number>"
      exit 1
    fi
    
    # PR番号が数値であることを確認
    if ! [[ "$PR_NUMBER" =~ ^[0-9]+$ ]]; then
      echo "Error: PR番号は数値である必要があります。"
      exit 1
    fi
    
    # pr-{pr_number}_{repoName} の形式でworktreeディレクトリを作成
    WORKTREE_NAME="pr-${PR_NUMBER}_${BASE_REPO_NAME}"
    WORKTREE_PATH="${PARENT_DIR}/${WORKTREE_NAME}"
    
    if [ -d "$WORKTREE_PATH" ]; then
      echo "Error: 既に ${WORKTREE_PATH} ディレクトリが存在します。"
      exit 1
    fi
    
    echo "PR #${PR_NUMBER} のブランチをチェックアウトしています..."
    
    # gh pr checkout を使用してPRブランチをチェックアウト
    if ! command -v gh >/dev/null 2>&1; then
      echo "Error: GitHub CLI (gh) がインストールされていません。"
      echo "GitHub CLI をインストールしてください: https://cli.github.com/"
      exit 1
    fi
    
    # PR情報を取得してブランチ名を確認
    PR_BRANCH=$(gh pr view "$PR_NUMBER" --json headRefName --jq '.headRefName' 2>/dev/null)
    if [ $? -ne 0 ] || [ -z "$PR_BRANCH" ]; then
      echo "Error: PR #${PR_NUMBER} が見つかりません。"
      exit 1
    fi
    
    echo "worktreeを ${WORKTREE_PATH} に作成します..."
    
    # リモートから最新の情報を取得
    echo "リモートから最新の情報を取得しています..."
    git fetch origin
    
    # ブランチが既に存在するかチェック
    if git show-ref --verify --quiet "refs/heads/$PR_BRANCH"; then
      # 既存のブランチでworktreeを作成
      git worktree add "$WORKTREE_PATH" "$PR_BRANCH"
    else
      # 新しいブランチを作成してworktreeを追加
      git worktree add -b "$PR_BRANCH" "$WORKTREE_PATH" "origin/$PR_BRANCH"
    fi
    
    if [ $? -ne 0 ]; then
      echo "Error: worktreeの作成に失敗しました。"
      exit 1
    fi
    
    echo "worktreeを正常に作成しました。"
    echo "worktreeディレクトリ: ${WORKTREE_PATH}"
    echo "PRブランチ: ${PR_BRANCH}"
    
    # 該当ブランチへ移動
    exec "$SHELL" -c "cd \"$WORKTREE_PATH\" && exec \"$SHELL\""
    ;;
  "-b")
    # 作成モード
    TARGET_BRANCH="$2"

    # ブランチ名に _ が含まれていた場合、エラーとする
    if echo "$TARGET_BRANCH" | grep -q "_"; then
      echo "Error: ブランチ名に _ が含まれています。ブランチ名には _ を使用しないでください。"
      exit 1
    fi

    # {branchName}_{repoName} の形式でworktreeディレクトリを作成
    # ブランチ名のスラッシュをハイフンに置換
    SAFE_BRANCH_NAME=$(echo "$TARGET_BRANCH" | sed 's/\//-/g')
    WORKTREE_NAME="${SAFE_BRANCH_NAME}_${BASE_REPO_NAME}"
    WORKTREE_PATH="${PARENT_DIR}/${WORKTREE_NAME}"

    if [ -d "$WORKTREE_PATH" ]; then
      echo "Error: 既に ${WORKTREE_PATH} ディレクトリが存在します。"
      echo "既存のworktreeを削除するには './worktree.sh -d ${TARGET_BRANCH}' を使用してください。"
      exit 1
    fi

    # ブランチが存在するかをチェック
    if git branch --list "$TARGET_BRANCH" | grep -q "$TARGET_BRANCH"; then
      echo "既存のブランチ ${TARGET_BRANCH} を使用してworktreeを作成します..."
      git worktree add "$WORKTREE_PATH" "$TARGET_BRANCH"
    else
      echo "新しいブランチ ${TARGET_BRANCH} を作成してworktreeを作成します..."
      git worktree add "$WORKTREE_PATH" -b "$TARGET_BRANCH"
    fi
    if [ $? -ne 0 ]; then
      echo "Error: worktreeの作成に失敗しました。"
      exit 1
    fi
    echo "worktreeを正常に作成しました。"
    echo "worktreeディレクトリ: ${WORKTREE_PATH}"

    # 該当ブランチへ移動
    exec "$SHELL" -c "cd \"$WORKTREE_PATH\" && exec \"$SHELL\""
    echo "ブランチ ${TARGET_BRANCH} に移動しました。"
    ;;
  "-d")
    # 削除モード
    TARGET_BRANCH="$2"
    
    # 引数がない場合はエラー
    if [ -z "$TARGET_BRANCH" ]; then
      echo "Error: 削除対象のブランチ名またはPR番号を指定してください。"
      echo "使用方法: ./worktree.sh -d <branchName> または ./worktree.sh -d <pr_number>"
      exit 1
    fi
    
    # PR番号かどうかを判定（数値のみの場合はPR番号とみなす）
    if [[ "$TARGET_BRANCH" =~ ^[0-9]+$ ]]; then
      # PR番号の場合
      PR_NUMBER="$TARGET_BRANCH"
      WORKTREE_NAME="pr-${PR_NUMBER}_${BASE_REPO_NAME}"
      
      # git worktree listから該当するworktreeを検索
      WORKTREE_PATH=$(git worktree list | grep "pr-${PR_NUMBER}_${BASE_REPO_NAME}" | awk '{print $1}')
      
      if [ -n "$WORKTREE_PATH" ] && [ -d "$WORKTREE_PATH" ]; then
        echo "PR #${PR_NUMBER} のworktreeディレクトリ ${WORKTREE_PATH} を削除します..."
        
        # 現在のディレクトリが削除対象の場合は、メインリポジトリに移動
        if [ "$(pwd)" = "$WORKTREE_PATH" ]; then
          echo "ディレクトリ ${MAIN_REPO_ROOT} に移動します。移動後もう一度実行してください。"
          exec "$SHELL" -c "cd \"${MAIN_REPO_ROOT}\" && exec \"$SHELL\""
          exit 0
        fi
        
        # worktreeを削除（パスで指定）
        git worktree remove "$WORKTREE_PATH"
        if [ $? -ne 0 ]; then
          echo "Error: worktreeディレクトリの削除に失敗しました。"
          exit 1
        else
          echo "worktreeディレクトリを削除しました。"
        fi
        
        # PR対応のブランチ名を取得して削除
        cd "${MAIN_REPO_ROOT}"
        
        # PRに対応するローカルブランチを探して削除
        if command -v gh >/dev/null 2>&1; then
          PR_BRANCH=$(gh pr view "$PR_NUMBER" --json headRefName --jq '.headRefName' 2>/dev/null)
          if [ $? -eq 0 ] && [ -n "$PR_BRANCH" ]; then
            # ローカルブランチが存在するかチェック
            if git branch --list "$PR_BRANCH" | grep -q "$PR_BRANCH"; then
              git branch -D "$PR_BRANCH"
              if [ $? -eq 0 ]; then
                echo "ブランチ ${PR_BRANCH} を削除しました。"
              else
                echo "Warning: ブランチ ${PR_BRANCH} の削除に失敗しました。"
              fi
            fi
          fi
        fi
      else
        echo "Error: PR #${PR_NUMBER} のworktreeディレクトリが見つかりません。"
        exit 1
      fi
    else
      # 通常のブランチ名の場合
      # git worktree listから該当するworktreeを検索（ブランチ名で検索）
      WORKTREE_PATH=""
      while IFS= read -r line; do
        if echo "$line" | grep -q "\[${TARGET_BRANCH}\]"; then
          WORKTREE_PATH=$(echo "$line" | awk '{print $1}')
          break
        fi
      done < <(git worktree list)
      
      if [ -n "$WORKTREE_PATH" ] && [ -d "$WORKTREE_PATH" ]; then
        echo "worktreeディレクトリ ${WORKTREE_PATH} を削除します..."
        
        # 現在のディレクトリが削除対象の場合は、メインリポジトリに移動
        if [ "$(pwd)" = "$WORKTREE_PATH" ]; then
          echo "ディレクトリ ${MAIN_REPO_ROOT} に移動します。移動後もう一度実行してください。"
          exec "$SHELL" -c "cd \"${MAIN_REPO_ROOT}\" && exec \"$SHELL\""
          exit 0
        fi
        
        # worktreeを削除（パスで指定）
        git worktree remove "$WORKTREE_PATH"
        if [ $? -ne 0 ]; then
          echo "Error: worktreeディレクトリの削除に失敗しました。"
          exit 1
        else
          echo "worktreeディレクトリを削除しました。"
        fi
        
        echo "worktreeのみを削除しました。ブランチ ${TARGET_BRANCH} は保持されています。"
      else
        echo "Error: ブランチ ${TARGET_BRANCH} のworktreeディレクトリが見つかりません。"
        echo "利用可能なworktree一覧を確認するには './worktree.sh -l' を使用してください。"
        exit 1
      fi
    fi
    ;;
  *)
    # 移動モード (オプションなし)
    TARGET_BRANCH="${1:-}"

    # 引数がない場合はヘルプを表示
    if [ -z "$TARGET_BRANCH" ]; then
      echo "=== Git Worktree管理スクリプト ==="
      echo
      echo "使用方法:"
      echo "  ./git_worktree/worktree.sh -l                   # worktree一覧を表示"
      echo "  ./git_worktree/worktree.sh <branchName>         # 指定ブランチのworktreeに移動"
      echo "  ./git_worktree/worktree.sh -b <branchName>      # ブランチとworktreeを作成して移動"
      echo "  ./git_worktree/worktree.sh -d <branchName>      # worktreeを削除（ブランチは保持）"
      echo "  ./git_worktree/worktree.sh -p <pr_number>       # PRのブランチでworktreeを作成"
      echo "  ./git_worktree/worktree.sh root                 # リポジトリのルートディレクトリに移動"
      exit 0
    fi

    # BASE_BRANCH または root の場合、 cd で移動するのみを行う
    if [ "$TARGET_BRANCH" = "$BASE_BRANCH" ] || [ "$TARGET_BRANCH" = "root" ]; then
      exec "$SHELL" -c "cd \"${MAIN_REPO_ROOT}\" && exec \"$SHELL\""
      echo "ディレクトリ ${MAIN_REPO_ROOT} に移動しました。"
      exit 0
    fi

    # ブランチ名のスラッシュをハイフンに置換
    SAFE_BRANCH_NAME=$(echo "$TARGET_BRANCH" | sed 's/\//-/g')
    WORKTREE_PATH="${PARENT_DIR}/${SAFE_BRANCH_NAME}_${BASE_REPO_NAME}"

    if [ ! -d "$WORKTREE_PATH" ]; then
      echo "Error: worktreeディレクトリ ${WORKTREE_PATH} が見つかりません。"
      echo "${TARGET_BRANCH} ブランチのworktreeを作成するには './worktree.sh -b ${TARGET_BRANCH}' を使用してください。"
      exit 1
    fi

    # worktreeディレクトリに移動
    echo "${WORKTREE_PATH} に移動します..."
    exec "$SHELL" -c "cd \"$WORKTREE_PATH\" && exec \"$SHELL\""
    echo "ディレクトリ ${WORKTREE_PATH} に移動しました。"
esac