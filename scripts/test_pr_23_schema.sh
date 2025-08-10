#!/bin/bash
# PR #23: スキーマ・モデル層の動作確認スクリプト

echo "========================================="
echo "PR #23: スキーマ・モデル層の動作確認"
echo "ブランチ: refactor/mykeibadb-schema"
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
git checkout refactor/mykeibadb-schema 2>/dev/null || {
    echo -e "${RED}エラー: ブランチが見つかりません${NC}"
    exit 1
}

# 2. MySQLコンテナの起動確認
echo -e "\n2️⃣ MySQLコンテナの確認"
if docker-compose ps mysql | grep -q "Up"; then
    echo -e "${GREEN}✅ MySQLコンテナは起動中${NC}"
else
    echo -e "${YELLOW}⚠️ MySQLコンテナを起動します${NC}"
    docker-compose up -d mysql
    sleep 10
fi

# 3. 新しいスキーマの適用
echo -e "\n3️⃣ mykeibaDBスキーマの適用"
run_test "init.sqlの実行" "docker-compose exec -T mysql mysql -uroot -proot_password keiba_db < docker/mysql/init.sql 2>/dev/null"

# 4. テーブル構造の確認
echo -e "\n4️⃣ テーブル構造の確認"

# 主要テーブルの存在確認
TABLES_TO_CHECK=(
    "RACE_SHOSAI"
    "KYOSOBA_MASTER2"
    "UMAGOTO_RACE_JOHO"
    "KISHU_MASTER"
    "CHOKYOSHI_MASTER"
    "BANUSHI_MASTER"
)

for table in "${TABLES_TO_CHECK[@]}"; do
    run_test "$table テーブルの存在" \
        "docker-compose exec mysql mysql -uroot -proot_password -e 'SHOW TABLES FROM keiba_db;' 2>/dev/null | grep -q $table"
done

# 5. SQLAlchemyモデルのインポートテスト
echo -e "\n5️⃣ SQLAlchemyモデルのインポートテスト"
cat > /tmp/test_models.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.getcwd())

try:
    from src.data.models.mykeibadb_models import (
        Base,
        RaceShosai,
        KyosobaMaster2,
        UmagotoRaceJoho,
        KishuMaster,
        ChokyoshiMaster,
        BanushiMaster
    )
    print("✅ すべてのモデルが正常にインポートされました")
    
    # テーブル名の確認
    print("\n📋 テーブル名マッピング:")
    print(f"  RaceShosai.__tablename__ = {RaceShosai.__tablename__}")
    print(f"  KyosobaMaster2.__tablename__ = {KyosobaMaster2.__tablename__}")
    print(f"  UmagotoRaceJoho.__tablename__ = {UmagotoRaceJoho.__tablename__}")
    
    sys.exit(0)
except Exception as e:
    print(f"❌ インポートエラー: {e}")
    sys.exit(1)
EOF

if [ -f "src/data/models/mykeibadb_models.py" ]; then
    run_test "Pythonモデルのインポート" "python3 /tmp/test_models.py"
else
    echo -e "${YELLOW}⚠️ モデルファイルが見つかりません${NC}"
fi

# 6. Row sizeエラー対策の確認
echo -e "\n6️⃣ Row sizeエラー対策設定の確認"
run_test "innodb_strict_mode = 0" \
    "docker-compose exec mysql mysql -uroot -proot_password -e 'SELECT @@innodb_strict_mode;' 2>/dev/null | grep -q '0'"

run_test "innodb_file_per_table = 1" \
    "docker-compose exec mysql mysql -uroot -proot_password -e 'SELECT @@innodb_file_per_table;' 2>/dev/null | grep -q '1'"

run_test "innodb_default_row_format = DYNAMIC" \
    "docker-compose exec mysql mysql -uroot -proot_password -e 'SELECT @@innodb_default_row_format;' 2>/dev/null | grep -qi 'dynamic'"

# 7. サンプルデータ挿入テスト
echo -e "\n7️⃣ サンプルデータ挿入テスト"
run_test "KEIBAJO_CODEへのデータ挿入" \
    "docker-compose exec mysql mysql -uroot -proot_password -e \"INSERT INTO keiba_db.KEIBAJO_CODE (CODE, NAME) VALUES ('99', 'テスト') ON DUPLICATE KEY UPDATE NAME=VALUES(NAME);\" 2>/dev/null"

# 結果サマリー
echo -e "\n========================================="
echo "テスト結果サマリー"
echo "========================================="
echo -e "${GREEN}✅ 成功: $TESTS_PASSED${NC}"
echo -e "${RED}❌ 失敗: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 すべてのテストが成功しました！${NC}"
    echo "PR #23は正常に動作しています。"
    exit 0
else
    echo -e "\n${RED}⚠️ 一部のテストが失敗しました${NC}"
    echo "上記のエラーを確認してください。"
    exit 1
fi