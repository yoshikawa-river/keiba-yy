from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Union

"""
基底バリデータークラス

すべてのバリデーターの基底となる抽象クラス
"""


@dataclass
class ValidationError:
    """バリデーションエラー情報"""

    field: str
    value: Any
    message: str
    error_type: str


@dataclass
class ValidationResult:
    """バリデーション結果"""

    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_error(
        self, field: str, value: Any, message: str, error_type: str = "validation_error"
    ):
        """エラーを追加"""
        self.errors.append(
            ValidationError(
                field=field, value=value, message=message, error_type=error_type
            )
        )
        self.is_valid = False

    def add_warning(self, message: str):
        """警告を追加"""
        self.warnings.append(message)

    def merge(self, other: "ValidationResult"):
        """他のバリデーション結果をマージ"""
        self.is_valid = self.is_valid and other.is_valid
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.metadata.update(other.metadata)


class BaseValidator(ABC):
    """基底バリデータークラス"""

    def __init__(self, strict_mode: bool = False):
        """
        バリデーターの初期化

        Args:
            strict_mode: 厳格モード(警告もエラーとして扱う)
        """
        self.strict_mode = strict_mode

    @abstractmethod
    def validate(self, data: Any) -> ValidationResult:
        """
        データをバリデーション

        Args:
            data: バリデーション対象データ

        Returns:
            バリデーション結果
        """
        pass

    def validate_batch(self, data_list: list[Any]) -> list[ValidationResult]:
        """
        複数データをバッチでバリデーション

        Args:
            data_list: バリデーション対象データのリスト

        Returns:
            バリデーション結果のリスト
        """
        results = []
        for data in data_list:
            results.append(self.validate(data))
        return results

    def _check_required_fields(
        self, data: dict[str, Any], required_fields: list[str]
    ) -> ValidationResult:
        """
        必須フィールドをチェック

        Args:
            data: チェック対象データ
            required_fields: 必須フィールドのリスト

        Returns:
            バリデーション結果
        """
        result = ValidationResult(is_valid=True)

        for field_name in required_fields:
            if (
                field_name not in data
                or data[field_name] is None
                or data[field_name] == ""
            ):
                result.add_error(
                    field=field_name,
                    value=None,
                    message=f"必須フィールド '{field_name}' が空です",
                    error_type="required_field_missing",
                )

        return result

    def _check_data_type(
        self, field: str, value: Any, expected_type: type
    ) -> Optional[ValidationError]:
        """
        データ型をチェック

        Args:
            field: フィールド名
            value: 値
            expected_type: 期待される型

        Returns:
            エラーがある場合はValidationError、なければNone
        """
        if value is None:
            return None

        if not isinstance(value, expected_type):
            return ValidationError(
                field=field,
                value=value,
                message=f"フィールド '{field}' の型が不正です。期待: {expected_type.__name__}, 実際: {type(value).__name__}",
                error_type="type_mismatch",
            )

        return None

    def _check_numeric_range(
        self,
        field: str,
        value: Any,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> Optional[ValidationError]:
        """
        数値の範囲をチェック

        Args:
            field: フィールド名
            value: 値
            min_value: 最小値
            max_value: 最大値

        Returns:
            エラーがある場合はValidationError、なければNone
        """
        if value is None:
            return None

        try:
            numeric_value = float(value)
        except (ValueError, TypeError):
            return ValidationError(
                field=field,
                value=value,
                message=f"フィールド '{field}' は数値である必要があります",
                error_type="not_numeric",
            )

        if min_value is not None and numeric_value < min_value:
            return ValidationError(
                field=field,
                value=value,
                message=f"フィールド '{field}' の値が最小値 {min_value} より小さいです",
                error_type="below_minimum",
            )

        if max_value is not None and numeric_value > max_value:
            return ValidationError(
                field=field,
                value=value,
                message=f"フィールド '{field}' の値が最大値 {max_value} より大きいです",
                error_type="above_maximum",
            )

        return None

    def _check_string_pattern(
        self, field: str, value: Any, pattern: str
    ) -> Optional[ValidationError]:
        """
        文字列パターンをチェック

        Args:
            field: フィールド名
            value: 値
            pattern: 正規表現パターン

        Returns:
            エラーがある場合はValidationError、なければNone
        """
        if value is None:
            return None

        import re

        if not isinstance(value, str):
            value = str(value)

        if not re.match(pattern, value):
            return ValidationError(
                field=field,
                value=value,
                message=f"フィールド '{field}' のフォーマットが不正です",
                error_type="pattern_mismatch",
            )

        return None

    def _check_enum_value(
        self, field: str, value: Any, valid_values: list[Any]
    ) -> Optional[ValidationError]:
        """
        列挙値をチェック

        Args:
            field: フィールド名
            value: 値
            valid_values: 有効な値のリスト

        Returns:
            エラーがある場合はValidationError、なければNone
        """
        if value is None:
            return None

        if value not in valid_values:
            return ValidationError(
                field=field,
                value=value,
                message=f"フィールド '{field}' の値が不正です。有効な値: {valid_values}",
                error_type="invalid_enum_value",
            )

        return None
