"""
スキーマバリデーター

データスキーマの検証機能を提供
"""

from collections.abc import Callable
from typing import Any, Union

from src.core.logging import logger
from src.data.validators.base_validator import BaseValidator, ValidationResult


class SchemaField:
    """スキーマフィールド定義"""

    def __init__(
        self,
        name: str,
        field_type: type,
        required: bool = False,
        min_value: float | None = None,
        max_value: float | None = None,
        pattern: str | None = None,
        enum_values: list[Any] | None = None,
        custom_validator: Callable[[Any], bool] | None = None,
    ):
        self.name = name
        self.field_type = field_type
        self.required = required
        self.min_value = min_value
        self.max_value = max_value
        self.pattern = pattern
        self.enum_values = enum_values
        self.custom_validator = custom_validator


class Schema:
    """データスキーマ定義"""

    def __init__(self, name: str, fields: list[SchemaField]):
        self.name = name
        self.fields = {field.name: field for field in fields}
        self.required_fields = [field.name for field in fields if field.required]


class SchemaValidator(BaseValidator):
    """スキーマバリデーター"""

    def __init__(self, schema: Schema, strict_mode: bool = False):
        """
        スキーマバリデーターの初期化

        Args:
            schema: スキーマ定義
            strict_mode: 厳格モード
        """
        super().__init__(strict_mode)
        self.schema = schema

    def validate(self, data: dict[str, Any]) -> ValidationResult:
        """
        スキーマに基づいてデータをバリデーション

        Args:
            data: バリデーション対象データ

        Returns:
            バリデーション結果
        """
        result = ValidationResult(is_valid=True)

        # 必須フィールドチェック
        required_result = self._check_required_fields(data, self.schema.required_fields)
        result.merge(required_result)

        # 各フィールドのバリデーション
        for field_name, field_def in self.schema.fields.items():
            if field_name in data:
                field_result = self._validate_field(
                    field_name, data[field_name], field_def
                )
                result.merge(field_result)

        # 不明なフィールドチェック
        if self.strict_mode:
            unknown_fields = set(data.keys()) - set(self.schema.fields.keys())
            for field in unknown_fields:
                result.add_warning(f"未定義のフィールド '{field}' が含まれています")

        # メタデータに検証情報を追加
        result.metadata["schema_name"] = self.schema.name
        result.metadata["validated_fields"] = len(self.schema.fields)
        result.metadata["total_errors"] = len(result.errors)
        result.metadata["total_warnings"] = len(result.warnings)

        return result

    def _validate_field(
        self, field_name: str, value: Any, field_def: SchemaField
    ) -> ValidationResult:
        """
        フィールドをバリデーション

        Args:
            field_name: フィールド名
            value: 値
            field_def: フィールド定義

        Returns:
            バリデーション結果
        """
        result = ValidationResult(is_valid=True)

        # NULL値チェック
        if value is None:
            if field_def.required:
                result.add_error(
                    field=field_name,
                    value=value,
                    message=f"必須フィールド '{field_name}' がNULLです",
                    error_type="null_value",
                )
            return result

        # 型チェック
        type_error = self._check_field_type(field_name, value, field_def.field_type)
        if type_error:
            result.errors.append(type_error)
            result.is_valid = False
            return result  # 型が不正な場合は他のチェックをスキップ

        # 数値範囲チェック
        if field_def.min_value is not None or field_def.max_value is not None:
            range_error = self._check_numeric_range(
                field_name, value, field_def.min_value, field_def.max_value
            )
            if range_error:
                result.errors.append(range_error)
                result.is_valid = False

        # パターンチェック
        if field_def.pattern:
            pattern_error = self._check_string_pattern(
                field_name, value, field_def.pattern
            )
            if pattern_error:
                result.errors.append(pattern_error)
                result.is_valid = False

        # 列挙値チェック
        if field_def.enum_values:
            enum_error = self._check_enum_value(
                field_name, value, field_def.enum_values
            )
            if enum_error:
                result.errors.append(enum_error)
                result.is_valid = False

        # カスタムバリデーター
        if field_def.custom_validator:
            try:
                custom_result = field_def.custom_validator(value)
                if custom_result is False:
                    result.add_error(
                        field=field_name,
                        value=value,
                        message="カスタムバリデーションに失敗しました",
                        error_type="custom_validation_failed",
                    )
                elif isinstance(custom_result, str):
                    result.add_error(
                        field=field_name,
                        value=value,
                        message=custom_result,
                        error_type="custom_validation_failed",
                    )
            except Exception as e:
                logger.error(f"カスタムバリデーターエラー: {e}")
                result.add_error(
                    field=field_name,
                    value=value,
                    message=f"カスタムバリデーターエラー: {e!s}",
                    error_type="custom_validator_error",
                )

        return result

    def _check_field_type(
        self, field: str, value: Any, expected_type: type
    ) -> Any | None:
        """
        フィールドの型をチェック(Union型対応)

        Args:
            field: フィールド名
            value: 値
            expected_type: 期待される型

        Returns:
            エラーがある場合はValidationError、なければNone
        """
        # Union型の処理
        if hasattr(expected_type, "__origin__") and expected_type.__origin__ is Union:
            for union_type in expected_type.__args__:
                if union_type is type(None) and value is None:
                    return None
                if isinstance(value, union_type):
                    return None
            return self._check_data_type(field, value, expected_type)

        # 通常の型チェック
        return self._check_data_type(field, value, expected_type)


# 事前定義されたスキーマ
class PredefinedSchemas:
    """事前定義されたスキーマ集"""

    @staticmethod
    def race_schema() -> Schema:
        """レース情報スキーマ"""
        return Schema(
            "race",
            [
                SchemaField("race_key", str, required=True, pattern=r"^\d{12}$"),
                SchemaField(
                    "race_date", str, required=True, pattern=r"^\d{4}-\d{2}-\d{2}$"
                ),
                SchemaField(
                    "race_number", int, required=True, min_value=1, max_value=12
                ),
                SchemaField("race_name", str, required=True),
                SchemaField("venue_name", str, required=True),
                SchemaField(
                    "race_type",
                    str,
                    required=True,
                    enum_values=["芝", "ダート", "障害"],
                ),
                SchemaField(
                    "distance", int, required=True, min_value=800, max_value=3600
                ),
                SchemaField(
                    "weather", str, enum_values=["晴", "曇", "雨", "小雨", "雪"]
                ),
                SchemaField(
                    "track_condition", str, enum_values=["良", "稍重", "重", "不良"]
                ),
                SchemaField(
                    "grade", str, enum_values=["G1", "G2", "G3", "OP", "L", None]
                ),
            ],
        )

    @staticmethod
    def horse_schema() -> Schema:
        """馬情報スキーマ"""
        return Schema(
            "horse",
            [
                SchemaField("horse_key", str, required=True, pattern=r"^\d{8,}$"),
                SchemaField("name", str, required=True),
                SchemaField("sex", str, required=True, enum_values=["牡", "牝", "騸"]),
                SchemaField("age", int, required=True, min_value=1, max_value=30),
                SchemaField("birth_date", str, pattern=r"^\d{4}-\d{2}-\d{2}$"),
                SchemaField(
                    "color",
                    str,
                    enum_values=["鹿毛", "黒鹿毛", "栗毛", "栃栗毛", "芦毛", "白毛"],
                ),
                SchemaField("sire_name", str),
                SchemaField("dam_name", str),
                SchemaField("breeder", str),
                SchemaField("owner", str),
            ],
        )

    @staticmethod
    def race_result_schema() -> Schema:
        """レース結果スキーマ"""
        return Schema(
            "race_result",
            [
                SchemaField("race_key", str, required=True, pattern=r"^\d{12}$"),
                SchemaField(
                    "post_position", int, required=True, min_value=1, max_value=28
                ),
                SchemaField("horse_key", str, required=True, pattern=r"^\d{8,}$"),
                SchemaField("jockey_key", str, required=True, pattern=r"^\d{4,}$"),
                SchemaField(
                    "weight_carried",
                    float,
                    required=True,
                    min_value=48.0,
                    max_value=65.0,
                ),
                SchemaField("finish_position", int, min_value=1, max_value=28),
                SchemaField("finish_time", str, pattern=r"^\d+:\d{2}\.\d$"),
                SchemaField("win_odds", float, min_value=1.0),
                SchemaField("favorite_order", int, min_value=1, max_value=28),
            ],
        )

    @staticmethod
    def odds_schema() -> Schema:
        """オッズ情報スキーマ"""
        return Schema(
            "odds",
            [
                SchemaField("race_key", str, required=True, pattern=r"^\d{12}$"),
                SchemaField("recorded_at", str, required=True),
                SchemaField(
                    "odds_type",
                    str,
                    required=True,
                    enum_values=[
                        "win",
                        "place",
                        "exacta",
                        "quinella",
                        "wide",
                        "trio",
                        "trifecta",
                    ],
                ),
                SchemaField("combination", str, required=True),
                SchemaField("odds_value", float, required=True, min_value=1.0),
                SchemaField("popularity", int, min_value=1),
                SchemaField("vote_count", int, min_value=0),
                SchemaField("support_rate", float, min_value=0.0, max_value=100.0),
            ],
        )
