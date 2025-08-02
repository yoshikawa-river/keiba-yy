#!/usr/bin/env python
"""
SQLAlchemyリレーション動作確認スクリプト

モデル間のリレーションが正しく機能するかテスト
"""

import os
import sys
from datetime import date
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parents[2]
sys.path.append(str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.data.models import (
    Horse,
    Jockey,
    Race,
    Racecourse,
    RaceEntry,
    RaceResult,
    Trainer,
)


def get_database_url():
    """データベースURL取得"""
    host = os.getenv("DATABASE_HOST", "mysql")
    port = os.getenv("DATABASE_PORT", "3306")
    user = os.getenv("DATABASE_USER", "keiba_user")
    password = os.getenv("DATABASE_PASSWORD", "keiba_password")
    database = os.getenv("DATABASE_NAME", "keiba_db")

    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


def test_relations():
    """リレーションテスト"""
    print("=== SQLAlchemyリレーション動作確認 ===\n")

    # データベース接続
    engine = create_engine(get_database_url(), echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. 競馬場データ作成
        print("1. 競馬場データ作成...")
        tokyo = session.query(Racecourse).filter_by(jra_code="05").first()
        if not tokyo:
            print("  ❌ 東京競馬場が見つかりません")
            return
        print(f"  ✅ 競馬場: {tokyo.name} (ID: {tokyo.id})")

        # 2. レースデータ作成
        print("\n2. テストレースデータ作成...")
        test_race = Race(
            race_key="20250101050112",
            race_date=date(2025, 1, 1),
            racecourse_id=tokyo.id,
            race_number=12,
            race_name="テストレース",
            race_type="芝",
            distance=2000,
            entry_count=16,
        )
        session.add(test_race)
        session.flush()  # IDを取得するためflush
        print(f"  ✅ レース作成: {test_race.race_name} (ID: {test_race.id})")

        # リレーション確認
        print(f"  📋 レース→競馬場: {test_race.racecourse.name}")

        # 3. 馬データ作成
        print("\n3. テスト馬データ作成...")
        test_horse = Horse(
            horse_id="2020100001",
            name="テストホース",
            sex="牡",
            birth_date=date(2020, 4, 1),
        )
        session.add(test_horse)
        session.flush()
        print(f"  ✅ 馬作成: {test_horse.name} (ID: {test_horse.id})")

        # 4. 騎手データ作成
        print("\n4. テスト騎手データ作成...")
        test_jockey = Jockey(jockey_id="00001", name="テスト騎手")
        session.add(test_jockey)
        session.flush()
        print(f"  ✅ 騎手作成: {test_jockey.name} (ID: {test_jockey.id})")

        # 5. 調教師データ作成
        print("\n5. テスト調教師データ作成...")
        test_trainer = Trainer(
            trainer_id="00001", name="テスト調教師", belonging="美浦"
        )
        session.add(test_trainer)
        session.flush()
        print(f"  ✅ 調教師作成: {test_trainer.name} (ID: {test_trainer.id})")

        # 6. 出走データ作成
        print("\n6. 出走データ作成...")
        test_entry = RaceEntry(
            race_id=test_race.id,
            horse_id=test_horse.id,
            jockey_id=test_jockey.id,
            trainer_id=test_trainer.id,
            post_position=1,
            horse_number=1,
            weight_carried=57.0,
            age=3,
        )
        session.add(test_entry)
        session.flush()
        print(f"  ✅ 出走データ作成 (ID: {test_entry.id})")

        # リレーション確認
        print("\n📋 出走データのリレーション確認:")
        print(f"  - レース: {test_entry.race.race_name}")
        print(f"  - 馬: {test_entry.horse.name}")
        print(f"  - 騎手: {test_entry.jockey.name}")
        print(f"  - 調教師: {test_entry.trainer.name}")

        # 7. レース結果データ作成
        print("\n7. レース結果データ作成...")
        test_result = RaceResult(
            race_entry_id=test_entry.id,
            finish_position=1,
            last_3f_time=33.5,
            prize_money=10000000,
        )
        session.add(test_result)
        session.flush()
        print(f"  ✅ レース結果作成 (着順: {test_result.finish_position}着)")

        # リレーション確認
        print(f"  📋 結果→出走: 馬番{test_result.entry.horse_number}")

        # 8. 逆方向のリレーション確認
        print("\n8. 逆方向のリレーション確認:")

        # レースから出走データ取得
        print(f"\n  📋 レース「{test_race.race_name}」の出走馬:")
        for entry in test_race.entries:
            print(
                f"    - 馬番{entry.horse_number}: {entry.horse.name} ({entry.jockey.name}騎手)"
            )

        # 馬から出走履歴取得
        print(f"\n  📋 「{test_horse.name}」の出走履歴:")
        for entry in test_horse.race_entries:
            print(f"    - {entry.race.race_date}: {entry.race.race_name}")

        # 騎手から騎乗履歴取得
        print(f"\n  📋 「{test_jockey.name}」の騎乗履歴:")
        for entry in test_jockey.race_entries:
            print(
                f"    - {entry.race.race_date}: {entry.horse.name} ({entry.race.race_name})"
            )

        # 調教師から管理馬取得
        print(f"\n  📋 「{test_trainer.name}」の管理馬:")
        for entry in test_trainer.race_entries:
            print(f"    - {entry.horse.name} ({entry.race.race_name})")

        # 出走データから結果取得(1対1)
        print(f"\n  📋 出走データの結果: {test_entry.result.finish_position}着")

        print("\n✅ リレーションテスト成功!全てのリレーションが正常に動作しています。")

        # コミット(テストデータを保存する場合)
        # session.commit()

        # ロールバック(テストデータを削除する場合)
        session.rollback()
        print("\n🔄 テストデータをロールバックしました。")

    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        session.rollback()
        import traceback

        traceback.print_exc()
    finally:
        session.close()


def check_cascade_delete():
    """カスケード削除の確認"""
    print("\n\n=== カスケード削除テスト ===\n")

    engine = create_engine(get_database_url(), echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # テストデータ作成
        tokyo = session.query(Racecourse).filter_by(jra_code="05").first()

        test_race = Race(
            race_key="20250202050112",
            race_date=date(2025, 2, 2),
            racecourse_id=tokyo.id,
            race_number=12,
            race_name="カスケードテストレース",
            race_type="芝",
            distance=1600,
        )
        session.add(test_race)
        session.flush()

        print(f"1. レース作成: {test_race.race_name} (ID: {test_race.id})")

        # 出走データ作成(簡略化)
        horse = session.query(Horse).first()
        jockey = session.query(Jockey).first()

        if horse and jockey:
            entry = RaceEntry(
                race_id=test_race.id,
                horse_id=horse.id,
                jockey_id=jockey.id,
                post_position=1,
                horse_number=1,
                weight_carried=55.0,
                age=3,
            )
            session.add(entry)
            session.flush()
            print(f"2. 出走データ作成 (ID: {entry.id})")

            # レース削除
            session.delete(test_race)
            session.flush()
            print("3. レースを削除...")

            # 出走データが削除されているか確認
            deleted_entry = session.query(RaceEntry).filter_by(id=entry.id).first()
            if deleted_entry is None:
                print("  ✅ カスケード削除成功: 出走データも削除されました")
            else:
                print("  ❌ カスケード削除失敗: 出走データが残っています")

        session.rollback()

    except Exception as e:
        print(f"❌ エラー発生: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    test_relations()
    check_cascade_delete()
    print("\n=== テスト完了 ===")
