#!/usr/bin/env python3
"""
mykeibaDB → ローカルMySQL データ同期スクリプト
使用方法:
  python sync_mykeibadb.py full      # 全データ同期
  python sync_mykeibadb.py recent [days]  # 最近のデータ同期
  python sync_mykeibadb.py verify    # 同期検証
  python sync_mykeibadb.py schedule  # 定期実行
"""

import mysql.connector
import logging
from datetime import datetime, timedelta
import schedule
import time
import os
from typing import Dict, List, Tuple
from tqdm import tqdm

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/mykeibadb_sync.log'),
        logging.StreamHandler()
    ]
)

class MykeibaDBSync:
    def __init__(self):
        # 接続設定
        self.source_config = {
            'host': os.environ.get('MYKEIBADB_HOST', 'localhost'),
            'port': int(os.environ.get('MYKEIBADB_PORT', 3306)),
            'user': os.environ.get('MYKEIBADB_USER'),
            'password': os.environ.get('MYKEIBADB_PASS'),
            'database': os.environ.get('MYKEIBADB_NAME', 'mykeibadb')
        }
        
        self.target_config = {
            'host': os.environ.get('MYSQL_HOST', 'localhost'),
            'port': int(os.environ.get('MYSQL_PORT', 3306)),
            'user': os.environ.get('MYSQL_USER', 'root'),
            'password': os.environ.get('MYSQL_PASS', 'root_password'),
            'database': os.environ.get('MYSQL_DB', 'keiba_db')
        }
        
        # 同期対象テーブル（依存関係順）
        self.sync_tables = [
            # マスター系テーブル
            'KISHU_MASTER',        # 騎手マスター
            'CHOKYOSHI_MASTER',    # 調教師マスター
            'BANUSHI_MASTER',      # 馬主マスター
            'KYOSOBA_MASTER2',     # 競走馬マスター
            
            # レース系テーブル
            'RACE_SHOSAI',         # レース詳細
            'UMAGOTO_RACE_JOHO',   # 馬ごとレース情報
            
            # オッズ・払戻系テーブル
            'ODDS1_TANSHO',        # 単勝オッズ
            'ODDS1_FUKUSHO',       # 複勝オッズ
            'HARAIMODOSHI',        # 払戻情報
            
            # コードマスター系
            'KEIBAJO_CODE',        # 競馬場コード
            'GRADE_CODE',          # グレードコード
            'TRACK_CODE',          # トラックコード
            'TENKO_CODE',          # 天候コード
            'SEIBETSU_CODE'        # 性別コード
        ]
    
    def connect_source(self):
        """mykeibaDBに接続"""
        try:
            return mysql.connector.connect(**self.source_config)
        except mysql.connector.Error as e:
            logging.error(f"Failed to connect to mykeibaDB: {e}")
            raise
    
    def connect_target(self):
        """ローカルMySQLに接続"""
        try:
            return mysql.connector.connect(**self.target_config)
        except mysql.connector.Error as e:
            logging.error(f"Failed to connect to local MySQL: {e}")
            raise
    
    def get_table_structure(self, conn, table: str) -> str:
        """テーブル構造を取得"""
        cursor = conn.cursor()
        try:
            cursor.execute(f"SHOW CREATE TABLE {table}")
            result = cursor.fetchone()
            return result[1] if result else None
        except mysql.connector.Error as e:
            logging.error(f"Failed to get structure for {table}: {e}")
            return None
        finally:
            cursor.close()
    
    def create_tables(self):
        """ローカルにテーブルを作成"""
        logging.info("Creating tables in local MySQL...")
        
        source_conn = self.connect_source()
        target_conn = self.connect_target()
        target_cursor = target_conn.cursor()
        
        try:
            # 外部キー制約を一時無効化
            target_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            
            for table in self.sync_tables:
                # テーブル構造取得
                create_sql = self.get_table_structure(source_conn, table)
                if create_sql:
                    # 既存テーブルを削除
                    target_cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    # 新規作成
                    target_cursor.execute(create_sql)
                    logging.info(f"Created table: {table}")
                else:
                    logging.warning(f"Could not get structure for table: {table}")
            
            # 外部キー制約を有効化
            target_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            target_conn.commit()
            
        except mysql.connector.Error as e:
            logging.error(f"Error creating tables: {e}")
            target_conn.rollback()
            raise
        finally:
            source_conn.close()
            target_conn.close()
    
    def sync_table(self, table: str, where_clause: str = None):
        """個別テーブルを同期"""
        logging.info(f"Syncing table: {table}")
        
        source_conn = self.connect_source()
        target_conn = self.connect_target()
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        try:
            # 外部キー制約を一時無効化
            target_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            
            # データ取得
            query = f"SELECT * FROM {table}"
            if where_clause:
                query += f" WHERE {where_clause}"
            
            source_cursor.execute(query)
            rows = source_cursor.fetchall()
            
            if rows:
                # カラム情報取得
                source_cursor.execute(f"SHOW COLUMNS FROM {table}")
                columns = [col[0] for col in source_cursor.fetchall()]
                
                # 既存データ削除
                if where_clause:
                    target_cursor.execute(f"DELETE FROM {table} WHERE {where_clause}")
                else:
                    target_cursor.execute(f"TRUNCATE TABLE {table}")
                
                # バッチインサート
                placeholders = ', '.join(['%s'] * len(columns))
                insert_query = f"""
                    INSERT INTO {table} ({', '.join(columns)}) 
                    VALUES ({placeholders})
                """
                
                batch_size = 1000
                with tqdm(total=len(rows), desc=f"Importing {table}") as pbar:
                    for i in range(0, len(rows), batch_size):
                        batch = rows[i:i+batch_size]
                        target_cursor.executemany(insert_query, batch)
                        target_conn.commit()
                        pbar.update(len(batch))
            
            # 外部キー制約を有効化
            target_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            logging.info(f"{table}: Total {len(rows)} rows synced")
            
        except mysql.connector.Error as e:
            logging.error(f"Error syncing {table}: {e}")
            target_conn.rollback()
            raise
        except Exception as e:
            logging.error(f"Unexpected error syncing {table}: {e}")
            target_conn.rollback()
            raise
        finally:
            source_conn.close()
            target_conn.close()
    
    def sync_recent_data(self, days: int = 7):
        """最近のデータのみ同期"""
        logging.info(f"Syncing recent {days} days data...")
        
        # 日付条件
        since_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        # マスタデータは全件同期
        for table in ['KISHU_MASTER', 'CHOKYOSHI_MASTER', 'BANUSHI_MASTER', 'KYOSOBA_MASTER2']:
            self.sync_table(table)
        
        # レース関連データは期間指定で同期
        # KAISAI_NEN + KAISAI_GAPPIで日付を判定
        where_clause = f"CONCAT(KAISAI_NEN, KAISAI_GAPPI) >= '{since_date}'"
        
        self.sync_table('RACE_SHOSAI', where_clause)
        
        # UMAGOTO_RACE_JOHOは関連するレースのみ
        self.sync_table('UMAGOTO_RACE_JOHO', 
                       f"RACE_CODE IN (SELECT RACE_CODE FROM RACE_SHOSAI WHERE {where_clause})")
        
        # オッズ・払戻データ
        self.sync_table('ODDS1_TANSHO', 
                       f"RACE_CODE IN (SELECT RACE_CODE FROM RACE_SHOSAI WHERE {where_clause})")
        self.sync_table('ODDS1_FUKUSHO', 
                       f"RACE_CODE IN (SELECT RACE_CODE FROM RACE_SHOSAI WHERE {where_clause})")
        self.sync_table('HARAIMODOSHI', 
                       f"RACE_CODE IN (SELECT RACE_CODE FROM RACE_SHOSAI WHERE {where_clause})")
        
        # コードマスターは全件同期
        for table in ['KEIBAJO_CODE', 'GRADE_CODE', 'TRACK_CODE', 'TENKO_CODE', 'SEIBETSU_CODE']:
            self.sync_table(table)
        
        logging.info(f"Recent {days} days sync completed!")
    
    def full_sync(self):
        """全データを同期"""
        logging.info("Starting full sync...")
        start_time = datetime.now()
        
        # テーブル作成
        self.create_tables()
        
        # 全テーブル同期
        for table in self.sync_tables:
            self.sync_table(table)
        
        elapsed_time = datetime.now() - start_time
        logging.info(f"Full sync completed in {elapsed_time}!")
    
    def verify_sync(self):
        """同期結果を検証"""
        logging.info("Verifying sync...")
        
        source_conn = self.connect_source()
        target_conn = self.connect_target()
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        results = []
        for table in self.sync_tables:
            try:
                # 行数比較
                source_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                source_count = source_cursor.fetchone()[0]
                
                target_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                target_count = target_cursor.fetchone()[0]
                
                match = source_count == target_count
                status = "✓" if match else "✗"
                
                result = {
                    'table': table,
                    'source_count': source_count,
                    'target_count': target_count,
                    'match': match
                }
                results.append(result)
                
                if match:
                    logging.info(f"{status} {table}: {source_count} rows (OK)")
                else:
                    logging.warning(f"{status} {table}: Source={source_count}, Target={target_count} (MISMATCH)")
                    
            except mysql.connector.Error as e:
                logging.error(f"Error verifying {table}: {e}")
        
        source_conn.close()
        target_conn.close()
        
        # サマリー表示
        total_tables = len(results)
        matched_tables = sum(1 for r in results if r['match'])
        logging.info(f"\nVerification Summary: {matched_tables}/{total_tables} tables matched")
        
        return all(r['match'] for r in results)

def main():
    """メイン処理"""
    import sys
    
    # 環境変数チェック
    if not os.environ.get('MYKEIBADB_USER'):
        logging.error("MYKEIBADB_USER environment variable not set")
        print("Please set MYKEIBADB_USER and MYKEIBADB_PASS environment variables")
        sys.exit(1)
    
    sync = MykeibaDBSync()
    
    # コマンドライン引数で処理を分岐
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'full':
            sync.full_sync()
            sync.verify_sync()
            
        elif command == 'recent':
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            sync.sync_recent_data(days)
            
        elif command == 'verify':
            success = sync.verify_sync()
            sys.exit(0 if success else 1)
            
        elif command == 'schedule':
            # 定期実行
            schedule.every().day.at("06:00").do(sync.sync_recent_data, 1)
            schedule.every().sunday.at("03:00").do(sync.sync_recent_data, 7)
            
            logging.info("Scheduler started:")
            logging.info("  - Daily at 06:00: Sync last 1 day")
            logging.info("  - Sunday at 03:00: Sync last 7 days")
            
            while True:
                schedule.run_pending()
                time.sleep(60)
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    else:
        print("mykeibaDB Sync Tool")
        print("==================")
        print("Usage:")
        print("  python sync_mykeibadb.py full           # 全データ同期")
        print("  python sync_mykeibadb.py recent [days]  # 最近のデータ同期（デフォルト7日）")
        print("  python sync_mykeibadb.py verify         # 同期検証")
        print("  python sync_mykeibadb.py schedule       # 定期実行モード")
        print("\nEnvironment variables required:")
        print("  MYKEIBADB_USER: mykeibaDB username")
        print("  MYKEIBADB_PASS: mykeibaDB password")
        print("\nOptional environment variables:")
        print("  MYKEIBADB_HOST: mykeibaDB host (default: localhost)")
        print("  MYSQL_HOST: Local MySQL host (default: localhost)")
        print("  MYSQL_USER: Local MySQL user (default: root)")
        print("  MYSQL_PASS: Local MySQL password (default: root_password)")

if __name__ == "__main__":
    main()