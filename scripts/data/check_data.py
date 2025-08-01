#!/usr/bin/env python
"""
データベース内のデータ確認スクリプト
"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.data.models import Horse, Jockey, Trainer, Racecourse


def get_database_url():
    host = os.getenv("DATABASE_HOST", "mysql")
    port = os.getenv("DATABASE_PORT", "3306")
    user = os.getenv("DATABASE_USER", "keiba_user")
    password = os.getenv("DATABASE_PASSWORD", "keiba_password")
    database = os.getenv("DATABASE_NAME", "keiba_db")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


def check_data():
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("=== データベース内のデータ確認 ===\n")
        
        # 競馬場
        racecourses = session.query(Racecourse).all()
        print(f"競馬場: {len(racecourses)}件")
        for rc in racecourses[:3]:  # 最初の3件
            print(f"  - {rc.jra_code}: {rc.name}")
        
        # 馬
        horses = session.query(Horse).all()
        print(f"\n馬: {len(horses)}件")
        
        # 騎手
        jockeys = session.query(Jockey).all()
        print(f"騎手: {len(jockeys)}件")
        
        # 調教師
        trainers = session.query(Trainer).all()
        print(f"調教師: {len(trainers)}件")
        
    finally:
        session.close()


if __name__ == "__main__":
    check_data()