"""
バリデーターのユニットテスト
"""
from datetime import datetime, date
from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy.orm import Session

from src.data.validators import (
    BaseValidator,
    DataValidator,
    SchemaValidator,
    ValidationError,
    ValidationResult,
)
from src.data.validators.schema_validator import Schema, SchemaField
from src.data.validators.validation_rules import ValidationRules, DataQualityRules


class TestValidationResult:
    """ValidationResultのテスト"""

    def test_add_error(self):
        """エラー追加のテスト"""
        result = ValidationResult(is_valid=True)
        
        result.add_error("field1", "value1", "エラーメッセージ", "type1")
        
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].field == "field1"
        assert result.errors[0].value == "value1"
        assert result.errors[0].message == "エラーメッセージ"
        assert result.errors[0].error_type == "type1"

    def test_add_warning(self):
        """警告追加のテスト"""
        result = ValidationResult(is_valid=True)
        
        result.add_warning("警告メッセージ")
        
        assert result.is_valid  # 警告はis_validに影響しない
        assert len(result.warnings) == 1
        assert result.warnings[0] == "警告メッセージ"

    def test_merge(self):
        """結果のマージテスト"""
        result1 = ValidationResult(is_valid=True)
        result1.add_warning("警告1")
        result1.metadata["key1"] = "value1"
        
        result2 = ValidationResult(is_valid=False)
        result2.add_error("field2", "value2", "エラー2")
        result2.metadata["key2"] = "value2"
        
        result1.merge(result2)
        
        assert not result1.is_valid  # Falseが伝播
        assert len(result1.errors) == 1
        assert len(result1.warnings) == 1
        assert result1.metadata["key1"] == "value1"
        assert result1.metadata["key2"] == "value2"


class TestBaseValidator:
    """BaseValidatorのテスト"""

    class ConcreteValidator(BaseValidator):
        """テスト用の具象バリデーター"""
        
        def validate(self, data):
            return ValidationResult(is_valid=True)

    def test_check_required_fields(self):
        """必須フィールドチェックのテスト"""
        validator = self.ConcreteValidator()
        
        data = {"field1": "value1", "field2": None, "field3": ""}
        required_fields = ["field1", "field2", "field3", "field4"]
        
        result = validator._check_required_fields(data, required_fields)
        
        assert not result.is_valid
        assert len(result.errors) == 3  # field2, field3, field4

    def test_check_data_type(self):
        """データ型チェックのテスト"""
        validator = self.ConcreteValidator()
        
        # 正常ケース
        error = validator._check_data_type("field1", "text", str)
        assert error is None
        
        # エラーケース
        error = validator._check_data_type("field1", "text", int)
        assert error is not None
        assert error.field == "field1"
        assert "型が不正" in error.message

    def test_check_numeric_range(self):
        """数値範囲チェックのテスト"""
        validator = self.ConcreteValidator()
        
        # 正常ケース
        error = validator._check_numeric_range("field1", 50, 0, 100)
        assert error is None
        
        # 最小値エラー
        error = validator._check_numeric_range("field1", -10, 0, 100)
        assert error is not None
        assert "最小値" in error.message
        
        # 最大値エラー
        error = validator._check_numeric_range("field1", 150, 0, 100)
        assert error is not None
        assert "最大値" in error.message

    def test_check_string_pattern(self):
        """文字列パターンチェックのテスト"""
        validator = self.ConcreteValidator()
        
        # 正常ケース
        error = validator._check_string_pattern("field1", "20240101", r"^\d{8}$")
        assert error is None
        
        # エラーケース
        error = validator._check_string_pattern("field1", "abc", r"^\d{8}$")
        assert error is not None
        assert "フォーマットが不正" in error.message

    def test_check_enum_value(self):
        """列挙値チェックのテスト"""
        validator = self.ConcreteValidator()
        
        # 正常ケース
        error = validator._check_enum_value("field1", "A", ["A", "B", "C"])
        assert error is None
        
        # エラーケース
        error = validator._check_enum_value("field1", "D", ["A", "B", "C"])
        assert error is not None
        assert "値が不正" in error.message


class TestSchemaValidator:
    """SchemaValidatorのテスト"""

    @pytest.fixture
    def test_schema(self):
        """テスト用スキーマ"""
        return Schema("test", [
            SchemaField("id", int, required=True, min_value=1),
            SchemaField("name", str, required=True),
            SchemaField("age", int, min_value=0, max_value=150),
            SchemaField("status", str, enum_values=["active", "inactive"]),
            SchemaField("email", str, pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$"),
        ])

    def test_validate_valid_data(self, test_schema):
        """有効なデータのバリデーション"""
        validator = SchemaValidator(test_schema)
        
        data = {
            "id": 1,
            "name": "テスト太郎",
            "age": 30,
            "status": "active",
            "email": "test@example.com"
        }
        
        result = validator.validate(data)
        
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_missing_required(self, test_schema):
        """必須フィールド欠落のテスト"""
        validator = SchemaValidator(test_schema)
        
        data = {
            "id": 1,
            # "name"が欠落
            "age": 30
        }
        
        result = validator.validate(data)
        
        assert not result.is_valid
        assert any(e.field == "name" for e in result.errors)

    def test_validate_type_mismatch(self, test_schema):
        """型不一致のテスト"""
        validator = SchemaValidator(test_schema)
        
        data = {
            "id": "abc",  # 数値であるべき
            "name": "テスト",
        }
        
        result = validator.validate(data)
        
        assert not result.is_valid
        assert any(e.field == "id" and e.error_type == "type_mismatch" for e in result.errors)

    def test_validate_range_error(self, test_schema):
        """範囲エラーのテスト"""
        validator = SchemaValidator(test_schema)
        
        data = {
            "id": 0,  # 最小値1未満
            "name": "テスト",
            "age": 200,  # 最大値150超過
        }
        
        result = validator.validate(data)
        
        assert not result.is_valid
        assert len(result.errors) >= 2

    def test_validate_pattern_error(self, test_schema):
        """パターンエラーのテスト"""
        validator = SchemaValidator(test_schema)
        
        data = {
            "id": 1,
            "name": "テスト",
            "email": "invalid-email"
        }
        
        result = validator.validate(data)
        
        assert not result.is_valid
        assert any(e.field == "email" for e in result.errors)

    def test_validate_enum_error(self, test_schema):
        """列挙値エラーのテスト"""
        validator = SchemaValidator(test_schema)
        
        data = {
            "id": 1,
            "name": "テスト",
            "status": "unknown"
        }
        
        result = validator.validate(data)
        
        assert not result.is_valid
        assert any(e.field == "status" for e in result.errors)


class TestDataValidator:
    """DataValidatorのテスト"""

    @pytest.fixture
    def mock_session(self):
        """モックのDBセッション"""
        session = MagicMock(spec=Session)
        return session

    @pytest.fixture
    def validator(self, mock_session):
        """テスト用バリデーター"""
        return DataValidator(mock_session)

    def test_validate_race_duplicate_key(self, validator, mock_session):
        """レースキー重複チェックのテスト"""
        # 既存レースをモック
        mock_race = Mock()
        mock_session.query().filter_by().first.return_value = mock_race
        
        data = {
            "race_key": "202401010101",
            "race_name": "テストレース",
            "venue_name": "東京",
        }
        
        # 通常モード
        result = validator.validate_race(data)
        assert result.is_valid
        assert len(result.warnings) > 0
        
        # 厳格モード
        validator.strict_mode = True
        result = validator.validate_race(data)
        assert not result.is_valid

    def test_validate_race_future_date(self, validator, mock_session):
        """未来日付チェックのテスト"""
        mock_session.query().filter_by().first.return_value = None
        
        future_date = "2099-12-31"
        data = {
            "race_key": "209912310101",
            "race_date": future_date,
        }
        
        result = validator.validate_race(data)
        
        assert result.is_valid
        assert any("未来の日付" in w for w in result.warnings)

    def test_validate_horse_age_consistency(self, validator, mock_session):
        """馬の年齢整合性チェックのテスト"""
        mock_session.query().filter_by().first.return_value = None
        
        # 現在の年から計算して不一致になるようにテストデータを作成
        from datetime import date
        current_year = date.today().year
        birth_year = current_year - 10  # 10年前に生まれた馬
        
        data = {
            "horse_key": "20210001",
            "name": "テスト馬",
            "age": 5,  # 実際は10歳のはずなのに5歳と登録
            "birth_date": f"{birth_year}-01-01",
        }
        
        result = validator.validate_horse(data)
        
        assert result.is_valid
        assert any("年齢" in w and "一致しません" in w for w in result.warnings)

    def test_validate_race_result_references(self, validator, mock_session):
        """レース結果の参照チェックのテスト"""
        # レースは存在、馬と騎手は存在しない
        mock_session.query().filter_by().first.side_effect = [Mock(), None, None]
        
        data = {
            "race_key": "202401010101",
            "horse_key": "20210001",
            "jockey_key": "0001",
        }
        
        result = validator.validate_race_result(data)
        
        assert result.is_valid
        assert len(result.warnings) == 2  # 馬と騎手の警告

    def test_validate_odds_combination(self, validator, mock_session):
        """オッズ組み合わせチェックのテスト"""
        mock_session.query().filter_by().first.return_value = Mock()
        
        # 正常ケース（単勝）
        data = {
            "race_key": "202401010101",
            "odds_type": "win",
            "combination": "3",
        }
        result = validator.validate_odds(data)
        assert result.is_valid
        
        # エラーケース（単勝に複数馬番）
        data["combination"] = "3-5"
        result = validator.validate_odds(data)
        assert not result.is_valid


class TestValidationRules:
    """ValidationRulesのテスト"""

    def test_japanese_date_validator(self):
        """日本の日付形式バリデーターのテスト"""
        validator = ValidationRules.japanese_date_validator
        
        assert validator("2024-01-01") is True
        assert validator("2024/01/01") is True
        assert validator("2024年1月1日") is True
        assert validator("invalid") is False
        assert validator("") is True  # 空は許可

    def test_jra_race_key_validator(self):
        """JRAレースキーバリデーターのテスト"""
        validator = ValidationRules.jra_race_key_validator
        
        # 正常ケース
        assert validator("202401010101") is True
        
        # エラーケース
        assert validator("") != True
        assert validator("12345") != True  # 短すぎ
        assert validator("20240101010A") != True  # 文字が含まれる
        assert validator("202413010101") != True  # 不正な月

    def test_horse_weight_validator(self):
        """馬体重バリデーターのテスト"""
        validator = ValidationRules.horse_weight_validator
        
        assert validator(450) is True
        assert validator("450") is True
        assert validator(250) != True  # 軽すぎ
        assert validator(800) != True  # 重すぎ
        assert validator("abc") != True  # 数値でない

    def test_time_format_validator(self):
        """タイムフォーマットバリデーターのテスト"""
        validator = ValidationRules.time_format_validator
        
        assert validator("1:23.4") is True
        assert validator("83.4") is True
        assert validator("123.4") is True
        assert validator("1:234") != True  # 不正なフォーマット
        assert validator("abc") != True

    def test_odds_combination_validator(self):
        """オッズ組み合わせバリデーターのテスト"""
        # 単勝
        validator = ValidationRules.odds_combination_validator("win")
        assert validator("3") is True
        assert validator("3-5") != True
        
        # 馬連
        validator = ValidationRules.odds_combination_validator("exacta")
        assert validator("3-5") is True
        assert validator("3") != True
        assert validator("3-3") != True  # 同じ馬番
        
        # 3連単
        validator = ValidationRules.odds_combination_validator("trifecta")
        assert validator("3-5-7") is True
        assert validator("3-5") != True
        assert validator("3-3-5") != True  # 重複


class TestDataQualityRules:
    """DataQualityRulesのテスト"""

    def test_check_completeness(self):
        """完全性チェックのテスト"""
        data = {
            "field1": "value1",
            "field2": None,
            "field3": "",
            "field4": "value4",
        }
        required_fields = ["field1", "field4"]
        
        result = DataQualityRules.check_completeness(data, required_fields)
        
        assert result["overall_completeness"] == 0.5  # 2/4
        assert result["required_completeness"] == 1.0  # 2/2
        assert result["filled_fields"] == 2
        assert result["total_fields"] == 4

    def test_check_consistency(self):
        """一貫性チェックのテスト"""
        data_list = [
            {"field1": "a", "field2": "b", "field3": "c"},
            {"field1": "d", "field2": "e"},  # field3が欠落
            {"field1": "f", "field2": "g", "field3": "h"},
        ]
        
        result = DataQualityRules.check_consistency(data_list)
        
        assert not result["is_consistent"]
        assert len(result["issues"]) > 0
        assert set(result["common_fields"]) == {"field1", "field2"}
        assert set(result["all_fields"]) == {"field1", "field2", "field3"}