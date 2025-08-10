#!/bin/bash
# PR #24: データ同期機能の動作確認スクリプト

echo "========================================="
echo "PR #24: データ同期機能の動作確認"
echo "ブランチ: feature/mykeibadb-sync"
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
git checkout feature/mykeibadb-sync 2>/dev/null || {
    echo -e "${RED}エラー: ブランチが見つかりません${NC}"
    exit 1
}

# 2. 同期スクリプトの存在確認
echo -e "\n2️⃣ 同期スクリプトの存在確認"
run_test "sync_mykeibadb.pyの存在" "[ -f scripts/sync_mykeibadb.py ]"
run_test "test_mykeibadb_connection.pyの存在" "[ -f scripts/test_mykeibadb_connection.py ]"

# 3. データコンバーターの確認
echo -e "\n3️⃣ データコンバーターの確認"
run_test "data_converter.pyの存在" "[ -f src/data/converters/data_converter.py ]"

# 4. Python依存関係のテスト
echo -e "\n4️⃣ Python依存関係のテスト"
cat > /tmp/test_sync_imports.py << 'EOF'
#!/usr/bin/env python3
import sys
import os

try:
    # 必要なライブラリのインポートテスト
    import mysql.connector
    print("✅ mysql.connector: OK")
    
    import schedule
    print("✅ schedule: OK")
    
    from tqdm import tqdm
    print("✅ tqdm: OK")
    
    # データコンバーターのインポートテスト
    sys.path.insert(0, os.getcwd())
    from src.data.converters.data_converter import RaceKey
    print("✅ RaceKey: OK")
    
    print("\n✅ すべての依存関係が正常にインポートされました")
    sys.exit(0)
    
except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    print("必要なパッケージをインストールしてください:")
    print("  pip install mysql-connector-python schedule tqdm")
    sys.exit(1)
EOF

run_test "Python依存関係" "python3 /tmp/test_sync_imports.py"

# 5. 接続設定の確認
echo -e "\n5️⃣ 環境変数と接続設定の確認"
if [ -z "$MYKEIBADB_USER" ]; then
    echo -e "${YELLOW}⚠️ 注意: MYKEIBADB_USER環境変数が設定されていません${NC}"
    echo "  実際の同期を行う場合は以下を設定してください:"
    echo "  export MYKEIBADB_USER=your_username"
    echo "  export MYKEIBADB_PASS=your_password"
    echo "  export MYKEIBADB_HOST=mykeibadb_host"
else
    echo -e "${GREEN}✅ MYKEIBADB_USER環境変数が設定されています${NC}"
fi

# 6. ローカルMySQL接続テスト
echo -e "\n6️⃣ ローカルMySQL接続テスト"
cat > /tmp/test_local_mysql.py << 'EOF'
#!/usr/bin/env python3
import mysql.connector
import os

try:
    config = {
        'host': os.environ.get('MYSQL_HOST', 'localhost'),
        'port': int(os.environ.get('MYSQL_PORT', 3306)),
        'user': os.environ.get('MYSQL_USER', 'root'),
        'password': os.environ.get('MYSQL_PASS', 'root_password'),
        'database': os.environ.get('MYSQL_DB', 'keiba_db')
    }
    
    conn = mysql.connector.connect(**config)
    if conn.is_connected():
        print("✅ ローカルMySQLへの接続成功")
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'keiba_db'")
        count = cursor.fetchone()[0]
        print(f"  keiba_dbのテーブル数: {count}")
        
        cursor.close()
        conn.close()
        exit(0)
    else:
        print("❌ ローカルMySQLへの接続失敗")
        exit(1)
except Exception as e:
    print(f"❌ エラー: {e}")
    exit(1)
EOF

run_test "ローカルMySQL接続" "python3 /tmp/test_local_mysql.py"

# 7. 同期スクリプトのヘルプ表示テスト
echo -e "\n7️⃣ 同期スクリプトのヘルプ表示"
run_test "sync_mykeibadb.pyヘルプ" "python3 scripts/sync_mykeibadb.py 2>&1 | grep -q 'mykeibaDB Sync Tool'"

# 8. test_mykeibadb_connection.pyの実行（ドライラン）
echo -e "\n8️⃣ 接続テストスクリプトの実行"
if [ -n "$MYKEIBADB_USER" ]; then
    echo "実際のmykeibaDBへの接続をテストします..."
    python3 scripts/test_mykeibadb_connection.py
else
    echo -e "${YELLOW}⚠️ mykeibaDB認証情報が設定されていないため、スキップします${NC}"
fi

# 9. データ変換テスト
echo -e "\n9️⃣ データ変換機能のテスト"
cat > /tmp/test_converter.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.getcwd())

try:
    from src.data.converters.data_converter import RaceKey
    
    # RaceKeyのテスト
    race_key = RaceKey.from_race_id("20240101050101")
    print(f"✅ RaceKey変換成功:")
    print(f"  Year: {race_key.year}")
    print(f"  Jyo CD: {race_key.jyo_cd}")
    print(f"  Kaiji: {race_key.kaiji}")
    print(f"  Nichiji: {race_key.nichiji}")
    print(f"  Race Num: {race_key.race_num}")
    
    exit(0)
except Exception as e:
    print(f"❌ エラー: {e}")
    exit(1)
EOF

run_test "データ変換機能" "python3 /tmp/test_converter.py"

# 結果サマリー
echo -e "\n========================================="
echo "テスト結果サマリー"
echo "========================================="
echo -e "${GREEN}✅ 成功: $TESTS_PASSED${NC}"
echo -e "${RED}❌ 失敗: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 すべてのテストが成功しました！${NC}"
    echo "PR #24は正常に動作しています。"
    
    if [ -z "$MYKEIBADB_USER" ]; then
        echo -e "\n${YELLOW}📝 注意:${NC}"
        echo "実際のmykeibaDBからのデータ同期を行うには、"
        echo "環境変数を設定してください:"
        echo "  export MYKEIBADB_USER=your_username"
        echo "  export MYKEIBADB_PASS=your_password"
        echo "  export MYKEIBADB_HOST=mykeibadb_host"
    fi
    
    exit 0
else
    echo -e "\n${RED}⚠️ 一部のテストが失敗しました${NC}"
    echo "上記のエラーを確認してください。"
    exit 1
fi