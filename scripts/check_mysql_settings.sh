#!/bin/bash
# MySQL設定確認スクリプト

echo "========================================="
echo "MySQL Row Size設定確認"
echo "========================================="

# Docker MySQLに接続して設定を確認
docker-compose exec mysql mysql -uroot -p${DATABASE_ROOT_PASSWORD:-root_password} -e "
SELECT 
    'innodb_strict_mode' as setting_name, 
    @@innodb_strict_mode as current_value,
    CASE WHEN @@innodb_strict_mode = 0 THEN '✅ OK' ELSE '❌ NG' END as status
UNION ALL
SELECT 
    'innodb_file_per_table', 
    @@innodb_file_per_table,
    CASE WHEN @@innodb_file_per_table = 1 THEN '✅ OK' ELSE '❌ NG' END
UNION ALL
SELECT 
    'innodb_default_row_format', 
    @@innodb_default_row_format,
    CASE WHEN @@innodb_default_row_format = 'DYNAMIC' THEN '✅ OK' ELSE '⚠️ Warning' END
UNION ALL
SELECT 
    'max_allowed_packet', 
    @@max_allowed_packet,
    CASE WHEN @@max_allowed_packet >= 1073741824 THEN '✅ OK' ELSE '⚠️ Small' END
UNION ALL
SELECT 
    'innodb_buffer_pool_size', 
    @@innodb_buffer_pool_size,
    CASE WHEN @@innodb_buffer_pool_size >= 2147483648 THEN '✅ OK' ELSE '⚠️ Small' END;
"

echo ""
echo "========================================="
echo "設定値の説明:"
echo "========================================="
echo "innodb_strict_mode = 0        : Row sizeエラーを警告に変更（必須）"
echo "innodb_file_per_table = 1     : テーブルごとに個別ファイル（必須）"
echo "innodb_default_row_format = DYNAMIC : 大きなカラムを効率的に格納"
echo "max_allowed_packet >= 1GB     : 大量データの送受信に対応"
echo "innodb_buffer_pool_size >= 2GB: メモリキャッシュサイズ"
echo ""