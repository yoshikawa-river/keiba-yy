#!/usr/bin/env python3
"""
mykeibaDB接続タイムアウト問題の診断・修正スクリプト
"""

import mysql.connector
import socket
import time
import sys
import os
from mysql.connector import Error

def test_network_connectivity(host, port):
    """ネットワーク接続性をテスト"""
    print(f"\n1. ネットワーク接続テスト: {host}:{port}")
    print("-" * 50)
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # 10秒のタイムアウト
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ ポート {port} は開いています")
            return True
        else:
            print(f"❌ ポート {port} に接続できません")
            print("  → ファイアウォールやネットワーク設定を確認してください")
            return False
    except socket.gaierror:
        print(f"❌ ホスト名 '{host}' を解決できません")
        print("  → ホスト名が正しいか確認してください")
        return False
    except Exception as e:
        print(f"❌ ネットワークエラー: {e}")
        return False

def test_mysql_connection_with_retry(config, max_retries=3):
    """MySQLへの接続を再試行付きでテスト"""
    print(f"\n2. MySQL接続テスト（最大{max_retries}回再試行）")
    print("-" * 50)
    
    for attempt in range(1, max_retries + 1):
        print(f"\n試行 {attempt}/{max_retries}...")
        
        try:
            # 接続設定に長めのタイムアウトを設定
            connection_config = {
                **config,
                'connection_timeout': 30,  # 30秒のタイムアウト
                'autocommit': True,
                'use_pure': True,  # Pure Python実装を使用（安定性向上）
                'raise_on_warnings': False,
                'auth_plugin': 'mysql_native_password',
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci'
            }
            
            print(f"  接続中... (タイムアウト: {connection_config['connection_timeout']}秒)")
            start_time = time.time()
            
            conn = mysql.connector.connect(**connection_config)
            
            if conn.is_connected():
                elapsed_time = time.time() - start_time
                print(f"  ✅ 接続成功！ (接続時間: {elapsed_time:.2f}秒)")
                
                # バージョン情報取得
                cursor = conn.cursor()
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
                print(f"  MySQL Version: {version[0]}")
                
                # 接続パラメータ確認
                cursor.execute("SHOW VARIABLES LIKE 'max_connections'")
                max_conn = cursor.fetchone()
                print(f"  最大接続数: {max_conn[1]}")
                
                cursor.execute("SHOW VARIABLES LIKE 'connect_timeout'")
                conn_timeout = cursor.fetchone()
                print(f"  サーバー側タイムアウト: {conn_timeout[1]}秒")
                
                cursor.close()
                conn.close()
                return True
                
        except Error as e:
            print(f"  ❌ 接続失敗: {e}")
            
            if e.errno == 2003:
                print("    → MySQLサーバーに接続できません")
                print("    → ホスト名とポートを確認してください")
            elif e.errno == 1045:
                print("    → 認証エラー: ユーザー名またはパスワードが間違っています")
            elif e.errno == 1049:
                print("    → データベースが存在しません")
            elif "Timeout" in str(e):
                print("    → タイムアウトエラー")
                print("    → ネットワークが遅いか、サーバーが過負荷の可能性があります")
            
            if attempt < max_retries:
                wait_time = attempt * 5  # 段階的に待機時間を増やす
                print(f"  {wait_time}秒待機してから再試行します...")
                time.sleep(wait_time)
        
        except Exception as e:
            print(f"  ❌ 予期しないエラー: {e}")
            
            if attempt < max_retries:
                print(f"  5秒待機してから再試行します...")
                time.sleep(5)
    
    return False

def suggest_connection_config():
    """推奨接続設定を提案"""
    print("\n3. 推奨される接続設定")
    print("-" * 50)
    print("""
以下の設定を.envファイルまたは接続スクリプトに追加してください：

```python
connection_config = {
    'host': 'your_host',
    'port': 3306,
    'user': 'your_user',
    'password': 'your_password',
    'database': 'mykeibadb',
    
    # タイムアウト対策
    'connection_timeout': 60,      # 接続タイムアウトを60秒に
    'read_timeout': 300,           # 読み込みタイムアウトを5分に
    'write_timeout': 300,          # 書き込みタイムアウトを5分に
    
    # 安定性向上
    'use_pure': True,              # Pure Python実装を使用
    'autocommit': True,            # 自動コミット
    'pool_size': 5,                # 接続プールサイズ
    'pool_reset_session': True,    # セッションリセット
    
    # SSL設定（必要に応じて）
    'use_ssl': False,              # SSLを使用しない場合
    
    # その他
    'auth_plugin': 'mysql_native_password',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}
```
    """)

def check_alternative_connections():
    """代替接続方法をチェック"""
    print("\n4. 代替接続方法の確認")
    print("-" * 50)
    
    print("""
以下の代替方法を試してください：

1. **VPN接続を使用**
   - 企業ネットワークの場合、VPN接続が必要な場合があります
   
2. **SSHトンネルを使用**
   ```bash
   ssh -L 3306:localhost:3306 user@mykeibadb-server
   ```
   
3. **プロキシ設定を確認**
   - 企業プロキシが設定されている場合、除外設定が必要です
   
4. **ホスト名の代わりにIPアドレスを使用**
   - DNSの問題を回避できます
   
5. **ポート番号を確認**
   - デフォルトの3306以外のポートを使用している可能性があります
    """)

def main():
    """メイン処理"""
    print("=" * 60)
    print("mykeibaDB接続タイムアウト診断ツール")
    print("=" * 60)
    
    # 環境変数から設定を読み込み
    config = {
        'host': os.environ.get('MYKEIBADB_HOST', 'localhost'),
        'port': int(os.environ.get('MYKEIBADB_PORT', 3306)),
        'user': os.environ.get('MYKEIBADB_USER'),
        'password': os.environ.get('MYKEIBADB_PASS'),
        'database': os.environ.get('MYKEIBADB_NAME', 'mykeibadb')
    }
    
    print(f"\n接続先情報:")
    print(f"  Host: {config['host']}")
    print(f"  Port: {config['port']}")
    print(f"  Database: {config['database']}")
    print(f"  User: {config['user'] if config['user'] else '(未設定)'}")
    
    if not config['user'] or not config['password']:
        print("\n❌ エラー: MYKEIBADB_USERとMYKEIBADB_PASSを環境変数に設定してください")
        print("\n例:")
        print("  export MYKEIBADB_USER=your_username")
        print("  export MYKEIBADB_PASS=your_password")
        print("  export MYKEIBADB_HOST=mykeibadb.example.com")
        return 1
    
    # ネットワーク接続テスト
    network_ok = test_network_connectivity(config['host'], config['port'])
    
    if network_ok:
        # MySQL接続テスト
        mysql_ok = test_mysql_connection_with_retry(config)
        
        if mysql_ok:
            print("\n" + "=" * 60)
            print("✅ 診断完了: 接続は正常です")
            print("=" * 60)
            return 0
        else:
            print("\n" + "=" * 60)
            print("⚠️ MySQL接続に失敗しました")
            suggest_connection_config()
            check_alternative_connections()
            print("=" * 60)
            return 1
    else:
        print("\n" + "=" * 60)
        print("❌ ネットワーク接続に問題があります")
        check_alternative_connections()
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())