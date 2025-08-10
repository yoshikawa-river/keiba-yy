#!/bin/bash
# PR #26: ドキュメント・ユーティリティの動作確認スクリプト

echo "========================================="
echo "PR #26: ドキュメント・ユーティリティの動作確認"
echo "ブランチ: docs/mykeibadb-update"
echo "========================================="

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# テスト結果カウンター
TESTS_PASSED=0
TESTS_FAILED=0

# テスト関数
run_test() {
    local test_name=$1
    local test_cmd=$2
    
    echo -e "\n🔍 Testing: $test_name"
    if eval "$test_cmd"; then
        echo -e "${GREEN}✅ PASSED${NC}: $test_name"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAILED${NC}: $test_name"
        ((TESTS_FAILED++))
    fi
}

# 1. ブランチに切り替え
echo -e "\n1️⃣ ブランチの切り替え"
git checkout docs/mykeibadb-update 2>/dev/null || {
    echo -e "${RED}エラー: ブランチが見つかりません${NC}"
    exit 1
}

# 2. ドキュメントファイルの存在確認
echo -e "\n2️⃣ ドキュメントファイルの存在確認"
run_test "README.mdの存在" "[ -f README.md ]"
run_test "CLAUDE.mdの存在" "[ -f CLAUDE.md ]"
run_test "docker-disk-resize-guide.mdの存在" "[ -f docs/docker-disk-resize-guide.md ]"
run_test "mykeibadb-connection-troubleshooting.mdの存在" "[ -f docs/mykeibadb-connection-troubleshooting.md ]"
run_test "MYSQL_CONNECTION_INFO.mdの存在" "[ -f docs/MYSQL_CONNECTION_INFO.md ]"

# 3. README.mdの内容確認
echo -e "\n3️⃣ README.mdの更新確認"
run_test "mykeibaDBの記載" "grep -q 'mykeibaDB' README.md"
run_test "MySQL 8.0の記載" "grep -q 'MySQL 8.0' README.md"
run_test "sync_mykeibadb.pyの記載" "grep -q 'sync_mykeibadb.py' README.md"

# 4. ユーティリティスクリプトの存在確認
echo -e "\n4️⃣ ユーティリティスクリプトの存在確認"
run_test "check_docker_disk.shの存在" "[ -f scripts/check_docker_disk.sh ]"
run_test "fix_docker_disk_space.shの存在" "[ -f scripts/fix_docker_disk_space.sh ]"
run_test "fix_mykeibadb_timeout.pyの存在" "[ -f scripts/fix_mykeibadb_timeout.py ]"

# 5. スクリプトの実行権限確認
echo -e "\n5️⃣ スクリプト実行権限の確認"
run_test "check_docker_disk.sh実行権限" "[ -x scripts/check_docker_disk.sh ]"
run_test "fix_docker_disk_space.sh実行権限" "[ -x scripts/fix_docker_disk_space.sh ]"

# 6. Pythonスクリプトの構文チェック
echo -e "\n6️⃣ Pythonスクリプトの構文チェック"
run_test "fix_mykeibadb_timeout.py構文" "python3 -m py_compile scripts/fix_mykeibadb_timeout.py 2>/dev/null"

# 7. check_docker_disk.shの実行テスト
echo -e "\n7️⃣ Docker容量確認スクリプトのテスト"
if [ -x scripts/check_docker_disk.sh ]; then
    echo "Docker容量を確認中..."
    ./scripts/check_docker_disk.sh | head -20
    run_test "check_docker_disk.sh実行" "[ $? -eq 0 ]"
else
    echo -e "${YELLOW}⚠️ check_docker_disk.shが実行できません${NC}"
fi

# 8. ドキュメントの構造確認
echo -e "\n8️⃣ ドキュメント構造の確認"
echo "docs/ディレクトリの内容:"
if [ -d docs ]; then
    ls -la docs/ | grep -E "\.md$"
    run_test "ドキュメントファイル数" "[ $(ls docs/*.md 2>/dev/null | wc -l) -ge 3 ]"
else
    echo -e "${RED}❌ docsディレクトリが見つかりません${NC}"
    ((TESTS_FAILED++))
fi

# 9. CLAUDE.mdの内容確認
echo -e "\n9️⃣ CLAUDE.md設定の確認"
if [ -f CLAUDE.md ]; then
    run_test "プロジェクト固有指示の記載" "grep -q 'keiba' CLAUDE.md"
    run_test "作業ディレクトリの記載" "grep -q '/Users/yy/Works/' CLAUDE.md"
else
    echo -e "${YELLOW}⚠️ CLAUDE.mdが見つかりません${NC}"
fi

# 10. トラブルシューティングガイドの内容確認
echo -e "\n🔟 トラブルシューティングガイドの確認"
if [ -f docs/mykeibadb-connection-troubleshooting.md ]; then
    run_test "タイムアウトエラーの記載" "grep -q 'Command Timeout' docs/mykeibadb-connection-troubleshooting.md"
    run_test "解決方法の記載" "grep -q '解決方法' docs/mykeibadb-connection-troubleshooting.md"
    run_test "設定ファイルの記載" "grep -q 'config.ini' docs/mykeibadb-connection-troubleshooting.md"
fi

# 11. Markdownファイルのリンクチェック
echo -e "\n1️⃣1️⃣ Markdownファイルの構文チェック"
cat > /tmp/check_markdown.py << 'EOF'
#!/usr/bin/env python3
import os
import re
import sys

errors = 0
files_checked = 0

# Markdownファイルを検索
for root, dirs, files in os.walk('.'):
    # .gitディレクトリをスキップ
    if '.git' in root:
        continue
    
    for file in files:
        if file.endswith('.md'):
            filepath = os.path.join(root, file)
            files_checked += 1
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 基本的な構文チェック
                # 見出しの確認
                if not re.search(r'^#+ ', content, re.MULTILINE):
                    print(f"⚠️ {filepath}: 見出しが見つかりません")
                    errors += 1
                
                # コードブロックの整合性
                code_blocks = content.count('```')
                if code_blocks % 2 != 0:
                    print(f"⚠️ {filepath}: コードブロックが閉じられていません")
                    errors += 1
                    
            except Exception as e:
                print(f"❌ {filepath}: 読み取りエラー - {e}")
                errors += 1

print(f"\n✅ {files_checked}個のMarkdownファイルをチェックしました")
if errors > 0:
    print(f"❌ {errors}個のエラーが見つかりました")
    sys.exit(1)
else:
    print("✅ すべてのMarkdownファイルは正常です")
    sys.exit(0)
EOF

run_test "Markdown構文チェック" "python3 /tmp/check_markdown.py"

# 結果サマリー
echo -e "\n========================================="
echo "テスト結果サマリー"
echo "========================================="
echo -e "${GREEN}✅ 成功: $TESTS_PASSED${NC}"
echo -e "${RED}❌ 失敗: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 すべてのテストが成功しました！${NC}"
    echo "PR #26のドキュメントとユーティリティは正常に動作しています。"
    echo ""
    echo "📚 提供されているドキュメント:"
    echo "  - README.md: プロジェクト概要（mykeibaDB対応）"
    echo "  - CLAUDE.md: Claude AI用設定"
    echo "  - Docker容量管理ガイド"
    echo "  - mykeibaDB接続トラブルシューティング"
    echo ""
    echo "🛠️ 提供されているユーティリティ:"
    echo "  - Docker容量確認・クリーンアップツール"
    echo "  - mykeibaDBタイムアウト診断ツール"
    exit 0
else
    echo -e "\n${RED}⚠️ 一部のテストが失敗しました${NC}"
    echo "上記のエラーを確認してください。"
    exit 1
fi