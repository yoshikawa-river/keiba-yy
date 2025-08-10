#!/usr/bin/env python3
"""
mykeibaDBへの接続テストスクリプト
Docker環境およびホストマシンからの接続をテストします
"""

import os
import sys
import time
import socket
from pathlib import Path
from typing import Optional, Dict, Any
import mysql.connector
from mysql.connector import Error


def test_mykeibadb_connection():
    """mykeibaDBへの接続をテスト"""
    
    print("=" * 60)
    print("mykeibaDB Connection Test")
    print("=" * 60)
    
    # 接続設定
    config = {
        'host': os.environ.get('MYKEIBADB_HOST', 'localhost'),
        'port': int(os.environ.get('MYKEIBADB_PORT', 3306)),
        'user': os.environ.get('MYKEIBADB_USER'),
        'password': os.environ.get('MYKEIBADB_PASS'),
        'database': os.environ.get('MYKEIBADB_NAME', 'mykeibadb')
    }
    
    print(f"Host: {config['host']}")
    print(f"Port: {config['port']}")
    print(f"Database: {config['database']}")
    print(f"User: {config['user']}")
    print()
    
    # 環境変数チェック
    if not config['user'] or not config['password']:
        print("❌ Error: MYKEIBADB_USER and MYKEIBADB_PASS environment variables must be set")
        return False
    
    # ネットワーク接続テスト
    print("1. Testing network connectivity...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((config['host'], config['port']))
        sock.close()
        
        if result == 0:
            print(f"✓ Successfully connected to {config['host']}:{config['port']}")
        else:
            print(f"❌ Cannot connect to {config['host']}:{config['port']}")
            return False
    except Exception as e:
        print(f"❌ Network error: {e}")
        return False
    
    # MySQL接続テスト
    print("\n2. Testing MySQL connection...")
    try:
        conn = mysql.connector.connect(**config)
        
        if conn.is_connected():
            print("✓ Successfully connected to mykeibaDB")
            
            cursor = conn.cursor()
            
            # バージョン情報取得
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"   MySQL Version: {version[0]}")
            
            # データベース情報
            cursor.execute("SELECT DATABASE()")
            db = cursor.fetchone()
            print(f"   Current Database: {db[0]}")
            
            # テーブル一覧確認
            print("\n3. Checking tables...")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            if tables:
                print(f"   Found {len(tables)} tables:")
                
                # 主要テーブルの存在確認
                main_tables = [
                    'RACE_SHOSAI',
                    'KYOSOBA_MASTER2',
                    'UMAGOTO_RACE_JOHO',
                    'KISHU_MASTER',
                    'CHOKYOSHI_MASTER',
                    'BANUSHI_MASTER'
                ]
                
                table_list = [t[0] for t in tables]
                
                for table in main_tables:
                    if table in table_list:
                        # 行数確認
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        print(f"   ✓ {table}: {count:,} rows")
                    else:
                        print(f"   ❌ {table}: Not found")
            else:
                print("   ⚠ No tables found")
            
            # 文字セット確認
            print("\n4. Checking character set...")
            cursor.execute("SHOW VARIABLES LIKE 'character_set_%'")
            charset_vars = cursor.fetchall()
            for var in charset_vars:
                if var[0] in ['character_set_database', 'character_set_connection']:
                    print(f"   {var[0]}: {var[1]}")
            
            cursor.close()
            conn.close()
            
            print("\n✅ All tests passed successfully!")
            return True
            
    except Error as e:
        print(f"❌ MySQL Error: {e}")
        
        if e.errno == 1045:
            print("   Access denied. Check username and password.")
        elif e.errno == 2003:
            print("   Cannot connect to MySQL server.")
        elif e.errno == 1049:
            print("   Unknown database.")
        
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_local_mysql_connection():
    """ローカルMySQLへの接続をテスト"""
    
    print("\n" + "=" * 60)
    print("Local MySQL Connection Test")
    print("=" * 60)
    
    # 接続設定
    config = {
        'host': os.environ.get('MYSQL_HOST', 'localhost'),
        'port': int(os.environ.get('MYSQL_PORT', 3306)),
        'user': os.environ.get('MYSQL_USER', 'root'),
        'password': os.environ.get('MYSQL_PASS', 'root_password'),
        'database': os.environ.get('MYSQL_DB', 'keiba_db')
    }
    
    print(f"Host: {config['host']}")
    print(f"Port: {config['port']}")
    print(f"Database: {config['database']}")
    print(f"User: {config['user']}")
    print()
    
    try:
        conn = mysql.connector.connect(**config)
        
        if conn.is_connected():
            print("✓ Successfully connected to local MySQL")
            
            cursor = conn.cursor()
            
            # テーブル一覧確認
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            if tables:
                print(f"   Found {len(tables)} tables")
                
                # 主要テーブルの存在確認
                main_tables = [
                    'RACE_SHOSAI',
                    'KYOSOBA_MASTER2',
                    'UMAGOTO_RACE_JOHO'
                ]
                
                table_list = [t[0] for t in tables]
                
                for table in main_tables:
                    if table in table_list:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        print(f"   ✓ {table}: {count:,} rows")
                    else:
                        print(f"   ⚠ {table}: Not found (will be created during sync)")
            else:
                print("   ⚠ No tables found (will be created during sync)")
            
            cursor.close()
            conn.close()
            
            return True
            
    except Error as e:
        print(f"❌ MySQL Error: {e}")
        return False


def main():
    """メイン処理"""
    
    print("mykeibaDB Connection Test Tool")
    print("=" * 60)
    print()
    
    # mykeibaDB接続テスト
    mykeibadb_ok = test_mykeibadb_connection()
    
    # ローカルMySQL接続テスト
    local_ok = test_local_mysql_connection()
    
    # サマリー
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    if mykeibadb_ok and local_ok:
        print("✅ All connections successful!")
        print("\nYou can now run:")
        print("  python sync_mykeibadb.py full    # to sync all data")
        print("  python sync_mykeibadb.py verify  # to verify sync")
        sys.exit(0)
    else:
        if not mykeibadb_ok:
            print("❌ mykeibaDB connection failed")
            print("\nPlease check:")
            print("  1. MYKEIBADB_USER and MYKEIBADB_PASS environment variables")
            print("  2. mykeibaDB host and port settings")
            print("  3. Network connectivity to mykeibaDB server")
        
        if not local_ok:
            print("❌ Local MySQL connection failed")
            print("\nPlease check:")
            print("  1. MySQL Docker container is running")
            print("  2. MySQL credentials are correct")
            print("  3. Database 'keiba_db' exists")
        
        sys.exit(1)


if __name__ == "__main__":
    main()