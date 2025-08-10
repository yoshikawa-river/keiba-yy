#!/usr/bin/env python3
"""
EvryDB2からMySQLサーバーへの接続テストスクリプト
Docker環境およびホストマシンからの接続をテストします
"""

import os
import socket
import sys
from pathlib import Path
from typing import Any

import mysql.connector
import yaml
from mysql.connector import Error


def load_config(config_path: str = "configs/evrydb2_connection.yaml") -> dict[str, Any]:
    """設定ファイルを読み込む"""
    config_file = Path(config_path)
    if not config_file.exists():
        print(f"設定ファイルが見つかりません: {config_path}")
        return {}

    with open(config_file) as f:
        config = yaml.safe_load(f)

    # 環境変数で値を置換
    def replace_env_vars(value):
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            if ":-" in env_var:
                var_name, default_value = env_var.split(":-", 1)
                return os.environ.get(var_name, default_value)
            return os.environ.get(env_var, value)
        return value

    def process_dict(d):
        for key, value in d.items():
            if isinstance(value, dict):
                process_dict(value)
            else:
                d[key] = replace_env_vars(value)

    process_dict(config)
    return config


def get_host_ip() -> str:
    """ホストマシンのIPアドレスを取得"""
    try:
        # Macの場合、en0またはen1インターフェースを確認
        import subprocess

        result = subprocess.run(
            ["ifconfig"], check=False, capture_output=True, text=True
        )
        lines = result.stdout.split("\n")

        for i, line in enumerate(lines):
            if "en0:" in line or "en1:" in line:
                # 次の行からIPアドレスを探す
                for j in range(i + 1, min(i + 10, len(lines))):
                    if "inet " in lines[j] and "127.0.0.1" not in lines[j]:
                        parts = lines[j].split()
                        inet_idx = parts.index("inet")
                        if inet_idx < len(parts) - 1:
                            return parts[inet_idx + 1]
    except Exception as e:
        print(f"IPアドレス取得エラー: {e}")

    # フォールバック
    hostname = socket.gethostname()
    return socket.gethostbyname(hostname)


def test_port_open(host: str, port: int, timeout: int = 5) -> bool:
    """指定されたホストとポートが開いているかテスト"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"ポート接続テストエラー: {e}")
        return False


def test_mysql_connection(
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    connection_name: str = "MySQL",
) -> bool:
    """MySQL接続をテスト"""
    print(f"\n{'=' * 50}")
    print(f"{connection_name} 接続テスト")
    print(f"{'=' * 50}")
    print(f"接続先: {host}:{port}")
    print(f"データベース: {database}")
    print(f"ユーザー: {user}")

    # ポートの疎通確認
    print(f"\n1. ポート {port} の疎通確認...")
    if not test_port_open(host, port):
        print(f"   ❌ ポート {port} に接続できません")
        return False
    print(f"   ✅ ポート {port} は開いています")

    # MySQL接続テスト
    print("\n2. MySQL接続テスト...")
    try:
        connection = mysql.connector.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            connection_timeout=10,
        )

        if connection.is_connected():
            print("   ✅ 接続成功!")

            # サーバー情報取得
            cursor = connection.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"   MySQL Server Version: {version[0]}")

            # データベース確認
            cursor.execute("SELECT DATABASE()")
            current_db = cursor.fetchone()
            print(f"   現在のデータベース: {current_db[0]}")

            # テーブル一覧取得
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"   テーブル数: {len(tables)}")
            if tables:
                print("   テーブル一覧:")
                for table in tables[:5]:  # 最初の5テーブルのみ表示
                    print(f"     - {table[0]}")
                if len(tables) > 5:
                    print(f"     ... 他 {len(tables) - 5} テーブル")

            cursor.close()
            connection.close()
            return True

    except Error as e:
        print(f"   ❌ 接続エラー: {e}")
        return False


def test_docker_internal_connection(config: dict[str, Any]) -> bool:
    """Docker内部からの接続テスト（host.docker.internal）"""
    db_config = config.get("database", {})
    return test_mysql_connection(
        host="host.docker.internal",
        port=int(db_config.get("port", 3306)),
        database=db_config.get("database", "keiba_db"),
        user=db_config.get("user", "keiba_user"),
        password=db_config.get("password", "keiba_password"),
        connection_name="Docker内部接続 (host.docker.internal)",
    )


def test_localhost_connection(config: dict[str, Any]) -> bool:
    """ローカルホストからの接続テスト"""
    db_config = config.get("database", {})
    return test_mysql_connection(
        host="localhost",
        port=int(db_config.get("port", 3306)),
        database=db_config.get("database", "keiba_db"),
        user=db_config.get("user", "keiba_user"),
        password=db_config.get("password", "keiba_password"),
        connection_name="ローカルホスト接続 (localhost)",
    )


def test_external_connection(config: dict[str, Any]) -> bool:
    """外部からの接続テスト（EvryDB2想定）"""
    external_config = config.get("external_connection", {})
    db_config = config.get("database", {})

    # 外部接続用のホストを取得（環境変数またはIPアドレス）
    external_host = external_config.get("host")
    if not external_host or external_host.startswith("${"):
        external_host = get_host_ip()
        print(f"\n自動検出されたホストIP: {external_host}")

    return test_mysql_connection(
        host=external_host,
        port=int(external_config.get("port", 3306)),
        database=db_config.get("database", "keiba_db"),
        user=db_config.get("user", "keiba_user"),
        password=db_config.get("password", "keiba_password"),
        connection_name="外部接続 (EvryDB2想定)",
    )


def main():
    """メイン処理"""
    print("=" * 60)
    print("EvryDB2 → MySQL接続テストツール")
    print("=" * 60)

    # 設定ファイル読み込み
    config = load_config()
    if not config:
        print("設定ファイルの読み込みに失敗しました")
        sys.exit(1)

    # 接続テスト結果
    results = []

    # 1. ローカルホスト接続テスト
    print("\n[テスト 1/3]")
    localhost_ok = test_localhost_connection(config)
    results.append(("ローカルホスト接続", localhost_ok))

    # 2. Docker内部接続テスト（Docker環境の場合のみ）
    if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER"):
        print("\n[テスト 2/3]")
        docker_ok = test_docker_internal_connection(config)
        results.append(("Docker内部接続", docker_ok))

    # 3. 外部接続テスト
    print("\n[テスト 3/3]")
    external_ok = test_external_connection(config)
    results.append(("外部接続（EvryDB2想定）", external_ok))

    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✅ 成功" if passed else "❌ 失敗"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ すべてのテストが成功しました！")
        print("EvryDB2からの接続が可能です。")
    else:
        print("⚠️ 一部のテストが失敗しました。")
        print("上記のエラーメッセージを確認してください。")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
