"""
CSVパーサーのユニットテスト
"""

from datetime import date, time
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from src.data.importers import (
    CSVFileDetector,
    FileType,
    HorseCSVParser,
    OddsCSVParser,
    RaceCSVParser,
    ResultCSVParser,
)
from src.data.models.race import Racecourse


class TestCSVFileDetector:
    """CSVFileDetectorのテスト"""

    def test_detect_file_type_race(self):
        """レースファイルの判定テスト"""
        detector = CSVFileDetector(Path("."))
        headers = ["レースID", "開催日", "R", "レース名", "競馬場", "コース", "距離"]

        file_type = detector._detect_file_type(headers)
        assert file_type == FileType.RACE_INFO

    def test_detect_file_type_horse(self):
        """馬ファイルの判定テスト"""
        detector = CSVFileDetector(Path("."))
        headers = ["馬ID", "馬名", "性別", "生年月日", "父", "母", "馬主"]

        file_type = detector._detect_file_type(headers)
        assert file_type == FileType.HORSE_INFO

    def test_detect_file_type_result(self):
        """結果ファイルの判定テスト"""
        detector = CSVFileDetector(Path("."))
        headers = ["着順", "馬名", "タイム", "オッズ", "馬番"]

        file_type = detector._detect_file_type(headers)
        assert file_type == FileType.RACE_RESULT

    def test_detect_file_type_odds(self):
        """オッズファイルの判定テスト"""
        detector = CSVFileDetector(Path("."))
        headers = ["馬番", "単勝", "複勝", "馬連", "馬単"]

        file_type = detector._detect_file_type(headers)
        assert file_type == FileType.ODDS_INFO

    def test_detect_file_type_unknown(self):
        """不明なファイルの判定テスト"""
        detector = CSVFileDetector(Path("."))
        headers = ["列1", "列2", "列3"]

        file_type = detector._detect_file_type(headers)
        assert file_type == FileType.UNKNOWN


class TestRaceCSVParser:
    """RaceCSVParserのテスト"""

    @pytest.fixture
    def mock_session(self):
        """モックのDBセッション"""
        return MagicMock(spec=Session)

    @pytest.fixture
    def parser(self, mock_session):
        """テスト用パーサーインスタンス"""
        return RaceCSVParser(mock_session)

    def test_column_mappings(self, parser):
        """カラムマッピングのテスト"""
        mappings = parser._get_column_mappings()
        assert mappings["レースID"] == "race_key"
        assert mappings["開催日"] == "race_date"
        assert mappings["競馬場"] == "venue_name"

    def test_required_columns(self, parser):
        """必須カラムのテスト"""
        required = parser._get_required_columns()
        assert "レースID" in required
        assert "開催日" in required
        assert "レース名" in required

    def test_transform_row_basic(self, parser):
        """基本的な行変換のテスト"""
        row = pd.Series(
            {
                "race_key": "202401010101",
                "race_date": "2024-01-01",
                "race_number": "1",
                "race_name": "新春特別",
                "venue_name": "東京",
                "track_type": "芝",
                "distance": "1600",
            }
        )

        result = parser._transform_row(row)

        assert result["race_key"] == "202401010101"
        assert result["race_date"] == date(2024, 1, 1)
        assert result["race_number"] == 1
        assert result["race_name"] == "新春特別"
        assert result["venue_name"] == "東京"
        assert result["race_type"] == "芝"
        assert result["distance"] == 1600

    def test_transform_row_with_optional(self, parser):
        """オプション項目を含む行変換のテスト"""
        row = pd.Series(
            {
                "race_key": "202401010101",
                "race_date": "2024-01-01",
                "race_number": "1",
                "race_name": "新春特別",
                "venue_name": "東京",
                "race_type": "芝",
                "distance": "1600",
                "weather": "晴",
                "track_condition": "良",
                "prize_money_1st": "1,000",
                "grade": "G3",
            }
        )

        result = parser._transform_row(row)

        assert result["weather"] == "晴"
        assert result["track_condition"] == "良"
        assert result["prize_money_1st"] == 1000
        assert result["grade"] == "G3"

    def test_validate_row_valid(self, parser):
        """有効な行のバリデーションテスト"""
        row = {
            "race_key": "202401010101",
            "race_number": 1,
            "venue_name": "東京",
            "distance": 1600,
            "race_type": "芝",
        }

        is_valid, error = parser._validate_row(row)
        assert is_valid is True
        assert error is None

    def test_validate_row_invalid_race_key(self, parser):
        """不正なレースキーのバリデーションテスト"""
        row = {
            "race_key": "invalid",
            "race_number": 1,
            "venue_name": "東京",
            "distance": 1600,
            "race_type": "芝",
        }

        is_valid, error = parser._validate_row(row)
        assert is_valid is False
        assert "不正なレースIDフォーマット" in error

    def test_save_row_new_race(self, parser, mock_session):
        """新規レース保存のテスト"""
        # 競馬場のモック
        Mock(spec=Racecourse, id=1)

        # queryチェーンのモック設定
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.side_effect = [
            None,
            None,
        ]  # 既存レースなし、既存競馬場なし
        mock_session.query.return_value = mock_query

        row_data = {
            "race_key": "202401010101",
            "race_date": date(2024, 1, 1),
            "race_number": 1,
            "race_name": "新春特別",
            "venue_name": "東京",
            "race_type": "芝",
            "distance": 1600,
        }

        # 保存実行
        result = parser._save_row(row_data)

        assert result is True
        assert mock_session.add.called
        assert parser.statistics["insert_count"] == 1


class TestHorseCSVParser:
    """HorseCSVParserのテスト"""

    @pytest.fixture
    def mock_session(self):
        """モックのDBセッション"""
        return MagicMock(spec=Session)

    @pytest.fixture
    def parser(self, mock_session):
        """テスト用パーサーインスタンス"""
        return HorseCSVParser(mock_session)

    def test_extract_sex(self, parser):
        """性別抽出のテスト"""
        assert parser._extract_sex("牡3") == "牡"
        assert parser._extract_sex("牝4") == "牝"
        assert parser._extract_sex("騸5") == "騸"
        assert parser._extract_sex("セ6") == "騸"

    def test_extract_age(self, parser):
        """年齢抽出のテスト"""
        assert parser._extract_age("牡3") == 3
        assert parser._extract_age("牝10") == 10
        assert parser._extract_age("騸15") == 15

    def test_normalize_color(self, parser):
        """毛色正規化のテスト"""
        assert parser._normalize_color("鹿") == "鹿毛"
        assert parser._normalize_color("黒鹿") == "黒鹿毛"
        assert parser._normalize_color("栗") == "栗毛"
        assert parser._normalize_color("芦") == "芦毛"

    def test_transform_row_basic(self, parser):
        """基本的な行変換のテスト"""
        row = pd.Series(
            {
                "horse_key": "20210001",
                "name": "テスト馬",
                "sex_age": "牡3",
            }
        )

        result = parser._transform_row(row)

        assert result["horse_key"] == "20210001"
        assert result["name"] == "テスト馬"
        assert result["sex"] == "牡"
        assert result["age"] == 3


class TestResultCSVParser:
    """ResultCSVParserのテスト"""

    @pytest.fixture
    def mock_session(self):
        """モックのDBセッション"""
        return MagicMock(spec=Session)

    @pytest.fixture
    def parser(self, mock_session):
        """テスト用パーサーインスタンス"""
        return ResultCSVParser(mock_session)

    def test_parse_finish_position(self, parser):
        """着順パースのテスト"""
        assert parser._parse_finish_position("1") == 1
        assert parser._parse_finish_position("15") == 15
        assert parser._parse_finish_position("中止") is None
        assert parser._parse_finish_position("除外") is None

    def test_parse_time(self, parser):
        """タイムパースのテスト"""
        # 分:秒.ミリ秒形式
        result = parser._parse_time("1:23.4")
        assert result == time(0, 1, 23, 400000)

        # 秒.ミリ秒形式
        result = parser._parse_time("83.4")
        assert result == time(0, 1, 23, 400000)

    def test_parse_margin(self, parser):
        """着差パースのテスト"""
        assert parser._parse_margin("ハナ") == "ハナ"
        assert parser._parse_margin("クビ") == "クビ"
        assert parser._parse_margin("1/2") == "1/2"
        assert parser._parse_margin("1.5") == "1.5"
        assert parser._parse_margin("大") == "大差"

    def test_parse_weight_change(self, parser):
        """体重増減パースのテスト"""
        assert parser._parse_weight_change("+2") == 2
        assert parser._parse_weight_change("-4") == -4
        assert parser._parse_weight_change("0") == 0


class TestOddsCSVParser:
    """OddsCSVParserのテスト"""

    @pytest.fixture
    def mock_session(self):
        """モックのDBセッション"""
        return MagicMock(spec=Session)

    @pytest.fixture
    def parser(self, mock_session):
        """テスト用パーサーインスタンス"""
        return OddsCSVParser(mock_session)

    def test_normalize_odds_type(self, parser):
        """オッズ種別正規化のテスト"""
        assert parser._normalize_odds_type("単勝") == "win"
        assert parser._normalize_odds_type("複勝") == "place"
        assert parser._normalize_odds_type("馬連") == "exacta"
        assert parser._normalize_odds_type("3連単") == "trifecta"

    def test_validate_combination_win(self, parser):
        """単勝組み合わせバリデーションのテスト"""
        assert parser._validate_combination("win", "3") is True
        assert parser._validate_combination("win", "3-5") is False
        assert parser._validate_combination("win", "abc") is False

    def test_validate_combination_exacta(self, parser):
        """馬連組み合わせバリデーションのテスト"""
        assert parser._validate_combination("exacta", "3-5") is True
        assert parser._validate_combination("exacta", "3") is False
        assert parser._validate_combination("exacta", "3-3") is False

    def test_validate_combination_trifecta(self, parser):
        """3連単組み合わせバリデーションのテスト"""
        assert parser._validate_combination("trifecta", "3-5-7") is True
        assert parser._validate_combination("trifecta", "3-5") is False
        assert parser._validate_combination("trifecta", "3-3-5") is False
