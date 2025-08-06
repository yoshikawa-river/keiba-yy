"""
SQLAlchemyモデルのユニットテスト

モデルの基本的な動作とリレーションのテスト
"""

from datetime import date, datetime, time
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.data.models import (
    Base,
    Horse,
    Jockey,
    OddsHistory,
    Prediction,
    Race,
    Racecourse,
    RaceEntry,
    RaceResult,
    Trainer,
)


@pytest.fixture
def db_session():
    """テスト用のインメモリデータベースセッション"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestRacecourseModel:
    """競馬場モデルのテスト"""

    def test_create_racecourse(self, db_session):
        """競馬場の作成テスト"""
        racecourse = Racecourse(
            jra_code="05",
            name="東京",
            name_kana="トウキョウ",
            location="東京都府中市",
        )
        db_session.add(racecourse)
        db_session.commit()

        assert racecourse.id is not None
        assert racecourse.jra_code == "05"
        assert racecourse.name == "東京"

    def test_racecourse_to_dict(self, db_session):
        """競馬場の辞書変換テスト"""
        racecourse = Racecourse(jra_code="06", name="中山")
        db_session.add(racecourse)
        db_session.commit()

        data = racecourse.to_dict()
        assert data["jra_code"] == "06"
        assert data["name"] == "中山"
        assert "created_at" in data


class TestRaceModel:
    """レースモデルのテスト"""

    def test_create_race(self, db_session):
        """レース作成テスト"""
        # 競馬場を先に作成
        racecourse = Racecourse(jra_code="05", name="東京")
        db_session.add(racecourse)
        db_session.commit()

        race = Race(
            race_key="20240301051200",
            race_date=date(2024, 3, 1),
            racecourse_id=racecourse.id,
            race_number=12,
            race_name="日本ダービー",
            race_type="芝",
            distance=2400,
            grade="G1",
            prize_money={"1st": 200000000, "2nd": 80000000},
        )
        db_session.add(race)
        db_session.commit()

        assert race.id is not None
        assert race.race_name == "日本ダービー"
        assert race.prize_money["1st"] == 200000000

    def test_race_racecourse_relation(self, db_session):
        """レースと競馬場のリレーションテスト"""
        racecourse = Racecourse(jra_code="09", name="阪神")
        db_session.add(racecourse)
        db_session.flush()  # IDを生成

        race = Race(
            race_key="20240301091100",
            race_date=date(2024, 3, 1),
            racecourse_id=racecourse.id,
            race_number=11,
            race_name="阪神大賞典",
            race_type="芝",
            distance=3000,
        )
        db_session.add(race)
        db_session.commit()

        # リレーションの確認
        assert race.racecourse.name == "阪神"
        assert len(racecourse.races) == 1
        assert racecourse.races[0].race_name == "阪神大賞典"


class TestHorseModel:
    """馬モデルのテスト"""

    def test_create_horse(self, db_session):
        """馬の作成テスト"""
        horse = Horse(
            horse_id="2021104123",
            name="エフフォーリア",
            sex="牡",
            birth_date=date(2018, 2, 11),
            color="鹿毛",
            father_name="エピファネイア",
            mother_name="ケイティーズハート",
        )
        db_session.add(horse)
        db_session.commit()

        assert horse.id is not None
        assert horse.name == "エフフォーリア"
        assert horse.sex == "牡"


class TestRaceEntryResult:
    """出走情報と結果のテスト"""

    def test_create_race_entry_with_result(self, db_session):
        """出走情報と結果の作成テスト"""
        # 必要なマスタデータを作成
        racecourse = Racecourse(jra_code="05", name="東京")
        horse = Horse(horse_id="2021104123", name="エフフォーリア", sex="牡")
        jockey = Jockey(jockey_id="00123", name="横山武史")
        trainer = Trainer(trainer_id="00456", name="鹿戸雄一", belonging="美浦")

        db_session.add_all([racecourse, horse, jockey, trainer])
        db_session.commit()

        race = Race(
            race_key="20240301051200",
            race_date=date(2024, 3, 1),
            racecourse_id=racecourse.id,
            race_number=12,
            race_name="日本ダービー",
            race_type="芝",
            distance=2400,
        )
        db_session.add(race)
        db_session.commit()

        # 出走情報
        entry = RaceEntry(
            race_id=race.id,
            horse_id=horse.id,
            jockey_id=jockey.id,
            trainer_id=trainer.id,
            post_position=7,
            horse_number=14,
            weight_carried=Decimal("57.0"),
            horse_weight=480,
            horse_weight_diff=-2,
            age=3,
            odds_win=Decimal("2.1"),
            popularity=1,
        )
        db_session.add(entry)
        db_session.commit()

        # 結果
        result = RaceResult(
            race_entry_id=entry.id,
            finish_position=1,
            finish_time=time(2, 24, 1),
            last_3f_time=Decimal("35.2"),
            corner_positions="7-7-5-3",
            prize_money=200000000,
        )
        db_session.add(result)
        db_session.commit()

        # リレーションの確認
        assert entry.horse.name == "エフフォーリア"
        assert entry.jockey.name == "横山武史"
        assert entry.result.finish_position == 1
        assert result.entry.horse_number == 14


class TestOddsHistory:
    """オッズ履歴のテスト"""

    def test_create_odds_history(self, db_session):
        """オッズ履歴の作成テスト"""
        racecourse = Racecourse(jra_code="05", name="東京")
        db_session.add(racecourse)
        db_session.commit()

        race = Race(
            race_key="20240301051200",
            race_date=date(2024, 3, 1),
            racecourse_id=racecourse.id,
            race_number=12,
            race_name="日本ダービー",
            race_type="芝",
            distance=2400,
        )
        db_session.add(race)
        db_session.commit()

        odds = OddsHistory(
            race_id=race.id,
            horse_number=1,
            odds_type="win",
            odds_value=Decimal("5.2"),
            recorded_at=datetime.now(),
        )
        db_session.add(odds)
        db_session.commit()

        assert odds.id is not None
        assert odds.odds_value == Decimal("5.2")


class TestPrediction:
    """予測結果のテスト"""

    def test_create_prediction(self, db_session):
        """予測結果の作成テスト"""
        racecourse = Racecourse(jra_code="05", name="東京")
        db_session.add(racecourse)
        db_session.commit()

        race = Race(
            race_key="20240301051200",
            race_date=date(2024, 3, 1),
            racecourse_id=racecourse.id,
            race_number=12,
            race_name="日本ダービー",
            race_type="芝",
            distance=2400,
        )
        db_session.add(race)
        db_session.commit()

        prediction_data = {
            "win_probabilities": {
                "1": 0.25,
                "2": 0.15,
                "3": 0.12,
            },
            "confidence": 0.85,
            "features_used": ["past_performance", "jockey_stats", "track_condition"],
        }

        prediction = Prediction(
            race_id=race.id,
            model_name="LightGBM_v1",
            model_version="1.0.0",
            prediction_data=prediction_data,
        )
        db_session.add(prediction)
        db_session.commit()

        assert prediction.id is not None
        assert prediction.prediction_data["confidence"] == 0.85
        assert len(prediction.prediction_data["features_used"]) == 3
