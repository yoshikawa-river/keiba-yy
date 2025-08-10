#!/bin/bash
# PR #25: プロジェクト設定の動作確認スクリプト

echo "========================================="
echo "PR #25: プロジェクト設定の動作確認"
echo "ブランチ: config/mykeibadb-settings"
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
git checkout config/mykeibadb-settings 2>/dev/null || {
    echo -e "${RED}エラー: ブランチが見つかりません${NC}"
    exit 1
}

# 2. 設定ファイルの存在確認
echo -e "\n2️⃣ 設定ファイルの存在確認"
run_test ".env.exampleの存在" "[ -f .env.example ]"
run_test "docker-compose.ymlの存在" "[ -f docker-compose.yml ]"
run_test "custom.cnfの存在" "[ -f docker/mysql/custom.cnf ]"
run_test "mykeibadb_connection.yamlの存在" "[ -f configs/mykeibadb_connection.yaml ]"
run_test "mykeibadb_tool_config.iniの存在" "[ -f configs/mykeibadb_tool_config.ini ]"

# 3. .env.exampleの設定確認
echo -e "\n3️⃣ 環境変数設定の確認"
run_test "MYKEIBADB_HOST設定" "grep -q 'MYKEIBADB_HOST=' .env.example"
run_test "MYKEIBADB_USER設定" "grep -q 'MYKEIBADB_USER=' .env.example"
run_test "MYKEIBADB_NAME設定" "grep -q 'MYKEIBADB_NAME=' .env.example"

# 4. MySQL設定の確認
echo -e "\n4️⃣ MySQL設定の確認（custom.cnf）"
run_test "innodb_strict_mode設定" "grep -q 'innodb_strict_mode = 0' docker/mysql/custom.cnf"
run_test "innodb_file_per_table設定" "grep -q 'innodb_file_per_table = 1' docker/mysql/custom.cnf"
run_test "innodb_default_row_format設定" "grep -q 'innodb_default_row_format = DYNAMIC' docker/mysql/custom.cnf"
run_test "max_allowed_packet設定" "grep -q 'max_allowed_packet' docker/mysql/custom.cnf"
run_test "innodb_buffer_pool_size設定" "grep -q 'innodb_buffer_pool_size' docker/mysql/custom.cnf"

# 5. docker-compose.ymlのMySQL設定マウント確認
echo -e "\n5️⃣ Docker Compose設定の確認"
run_test "custom.cnfのマウント設定" "grep -q 'custom.cnf:/etc/mysql/conf.d/custom.cnf' docker-compose.yml"

# 6. MySQLコンテナの再起動と設定適用確認
echo -e "\n6️⃣ MySQL設定の適用確認"
echo "MySQLコンテナを再起動して設定を適用します..."
docker-compose restart mysql 2>/dev/null
sleep 15

# 設定が適用されているか確認
run_test "innodb_strict_mode = 0 (適用確認)" \
    "docker-compose exec mysql mysql -uroot -proot_password -e 'SELECT @@innodb_strict_mode;' 2>/dev/null | grep -q '0'"

run_test "innodb_file_per_table = 1 (適用確認)" \
    "docker-compose exec mysql mysql -uroot -proot_password -e 'SELECT @@innodb_file_per_table;' 2>/dev/null | grep -q '1'"

run_test "innodb_default_row_format = DYNAMIC (適用確認)" \
    "docker-compose exec mysql mysql -uroot -proot_password -e 'SELECT @@innodb_default_row_format;' 2>/dev/null | grep -qi 'dynamic'"

run_test "max_allowed_packet >= 1GB (適用確認)" \
    "docker-compose exec mysql mysql -uroot -proot_password -e 'SELECT @@max_allowed_packet;' 2>/dev/null | awk '{if(\$1 >= 1073741824) exit 0; else exit 1}'"

# 7. check_mysql_settings.shスクリプトのテスト
echo -e "\n7️⃣ 設定確認スクリプトのテスト"
if [ -f scripts/check_mysql_settings.sh ]; then
    run_test "check_mysql_settings.sh実行" "bash scripts/check_mysql_settings.sh 2>&1 | grep -q 'innodb_strict_mode'"
else
    echo -e "${YELLOW}⚠️ check_mysql_settings.shが見つかりません${NC}"
fi

# 8. YAMLファイルの構文チェック
echo -e "\n8️⃣ YAML設定ファイルの構文チェック"
cat > /tmp/test_yaml.py << 'EOF'
#!/usr/bin/env python3
import yaml
import sys

try:
    with open('configs/mykeibadb_connection.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # 必須設定の確認
    assert 'database' in config, "database設定が見つかりません"
    assert 'connection_timeout' in config['database'], "connection_timeout設定が見つかりません"
    assert 'retry' in config, "retry設定が見つかりません"
    
    print("✅ YAML設定ファイルは正常です")
    print(f"  Connection Timeout: {config['database']['connection_timeout']}秒")
    print(f"  Max Retries: {config['retry']['max_attempts']}回")
    sys.exit(0)
    
except Exception as e:
    print(f"❌ エラー: {e}")
    sys.exit(1)
EOF

run_test "YAML設定ファイルの検証" "python3 /tmp/test_yaml.py"

# 9. Row size too largeエラーのテスト
echo -e "\n9️⃣ Row size too largeエラー対策のテスト"
echo "大きなテーブルを作成してテスト..."
cat > /tmp/test_row_size.sql << 'EOF'
CREATE TABLE IF NOT EXISTS test_large_row (
    id INT PRIMARY KEY,
    col1 VARCHAR(1000),
    col2 VARCHAR(1000),
    col3 VARCHAR(1000),
    col4 VARCHAR(1000),
    col5 VARCHAR(1000),
    col6 VARCHAR(1000),
    col7 VARCHAR(1000),
    col8 VARCHAR(1000),
    col9 TEXT,
    col10 TEXT
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC;

INSERT INTO test_large_row VALUES (1, 
    REPEAT('A', 1000), REPEAT('B', 1000), REPEAT('C', 1000),
    REPEAT('D', 1000), REPEAT('E', 1000), REPEAT('F', 1000),
    REPEAT('G', 1000), REPEAT('H', 1000),
    REPEAT('I', 5000), REPEAT('J', 5000)
);

DROP TABLE test_large_row;
EOF

run_test "Row size対策テスト" \
    "docker-compose exec -T mysql mysql -uroot -proot_password keiba_db < /tmp/test_row_size.sql 2>&1 | grep -v 'Warning'"

# 結果サマリー
echo -e "\n========================================="
echo "テスト結果サマリー"
echo "========================================="
echo -e "${GREEN}✅ 成功: $TESTS_PASSED${NC}"
echo -e "${RED}❌ 失敗: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 すべてのテストが成功しました！${NC}"
    echo "PR #25の設定は正常に動作しています。"
    echo ""
    echo "✅ MySQL最適化設定が適用されています"
    echo "✅ Row size too largeエラー対策が有効です"
    echo "✅ mykeibaDB接続設定が準備されています"
    exit 0
else
    echo -e "\n${RED}⚠️ 一部のテストが失敗しました${NC}"
    echo "上記のエラーを確認してください。"
    exit 1
fi