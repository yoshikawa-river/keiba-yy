#!/usr/bin/env python
"""
SQLAlchemyモデルの動作確認スクリプト

モデルの定義とリレーションが正しく機能するか確認
"""

import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.append(str(Path(__file__).parents[2]))

from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.data.models import Base, Horse, Jockey, Race, Racecourse, RaceEntry, Trainer


def main():
    """モデルの動作確認"""
    print("SQLAlchemyモデルの動作確認開始...")

    # インメモリデータベースで確認
    engine = create_engine("sqlite:///:memory:", echo=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. 競馬場作成
        print("\n1. 競馬場データ作成")
        tokyo = Racecourse(
            jra_code="05", name="東京", name_kana="トウキョウ", location="東京都府中市"
        )
        session.add(tokyo)
        session.commit()
        print(f"✓ 競馬場作成完了: {tokyo.name}")

        # 2. レース作成
        print("\n2. レースデータ作成")
        race = Race(
            race_key="20240301051200",
            race_date=date(2024, 3, 1),
            racecourse_id=tokyo.id,
            race_number=12,
            race_name="日本ダービー",
            race_type="芝",
            distance=2400,
            grade="G1",
            prize_money={"1st": 200000000, "2nd": 80000000},
        )
        session.add(race)
        session.commit()
        print(f"✓ レース作成完了: {race.race_name}")

        # 3. 馬、騎手、調教師作成
        print("\n3. 馬・騎手・調教師データ作成")
        horse = Horse(
            horse_id="2021104123",
            name="エフフォーリア",
            sex="牡",
            birth_date=date(2018, 2, 11),
        )
        jockey = Jockey(jockey_id="00123", name="横山武史")
        trainer = Trainer(trainer_id="00456", name="鹿戸雄一", belonging="美浦")

        session.add_all([horse, jockey, trainer])
        session.commit()
        print(f"✓ 馬: {horse.name}")
        print(f"✓ 騎手: {jockey.name}")
        print(f"✓ 調教師: {trainer.name}")

        # 4. 出走情報作成
        print("\n4. 出走情報作成")
        entry = RaceEntry(
            race_id=race.id,
            horse_id=horse.id,
            jockey_id=jockey.id,
            trainer_id=trainer.id,
            post_position=7,
            horse_number=14,
            weight_carried=Decimal("57.0"),
            age=3,
            odds_win=Decimal("2.1"),
            popularity=1,
        )
        session.add(entry)
        session.commit()
        print("✓ 出走情報作成完了")

        # 5. リレーション確認
        print("\n5. リレーション動作確認")
        # レース→競馬場
        print(f"✓ レース→競馬場: {race.racecourse.name}")
        # 競馬場→レース
        print(f"✓ 競馬場→レース数: {len(tokyo.races)}")
        # 出走情報→各種マスタ
        print(f"✓ 出走馬: {entry.horse.name}")
        print(f"✓ 騎手: {entry.jockey.name}")
        print(f"✓ 調教師: {entry.trainer.name}")

        # 6. to_dict()メソッド確認
        print("\n6. to_dict()メソッド確認")
        race_dict = race.to_dict()
        print(f"✓ レース辞書化: {list(race_dict.keys())[:5]}...")

        print("\n✅ 全てのテストが正常に完了しました!")

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        session.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
