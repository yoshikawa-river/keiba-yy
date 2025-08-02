"""
バリデーションルール定義

各種データタイプ用のバリデーションルールを定義
"""

from datetime import datetime
from typing import Any, Callable, Dict, List, Union

from src.data.validators.schema_validator import Schema, SchemaField


class ValidationRules:
    """バリデーションルール集"""

    @staticmethod
    def japanese_date_validator(value: Any) -> bool:
        """日本の日付形式をバリデーション"""
        if not value:
            return True

        try:
            # 複数の日付フォーマットを試す
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"]:
                try:
                    datetime.strptime(str(value), fmt)
                    return True
                except ValueError:
                    continue
            return False
        except Exception:
            return False

    @staticmethod
    def jra_race_key_validator(value: Any) -> Union[str, bool]:
        """JRAレースキーをバリデーション"""
        if not value:
            return "レースキーが空です"

        value_str = str(value)
        if len(value_str) != 12:
            return f"レースキーは12桁である必要があります（現在: {len(value_str)}桁）"

        if not value_str.isdigit():
            return "レースキーは数字のみで構成される必要があります"

        # YYYYMMDDRRNNフォーマットチェック
        year = int(value_str[:4])
        month = int(value_str[4:6])
        day = int(value_str[6:8])
        race_num = int(value_str[10:12])

        if year < 1900 or year > 2100:
            return f"年が不正です: {year}"

        if month < 1 or month > 12:
            return f"月が不正です: {month}"

        if day < 1 or day > 31:
            return f"日が不正です: {day}"

        if race_num < 1 or race_num > 12:
            return f"レース番号が不正です: {race_num}"

        return True

    @staticmethod
    def horse_weight_validator(value: Any) -> Union[str, bool]:
        """馬体重をバリデーション"""
        if not value:
            return True

        try:
            weight = int(value)
            if weight < 300 or weight > 700:
                return f"馬体重が異常です: {weight}kg（通常300-700kg）"
            return True
        except Exception:
            return "馬体重は数値である必要があります"

    @staticmethod
    def time_format_validator(value: Any) -> Union[str, bool]:
        """タイムフォーマットをバリデーション"""
        if not value:
            return True

        value_str = str(value)

        # 分:秒.ミリ秒 または 秒.ミリ秒 形式
        import re

        pattern1 = r"^\d{1,2}:\d{2}\.\d$"  # 1:23.4
        pattern2 = r"^\d{2,3}\.\d$"  # 83.4

        if re.match(pattern1, value_str) or re.match(pattern2, value_str):
            return True

        return "タイムフォーマットが不正です（例: 1:23.4 または 83.4）"

    @staticmethod
    def odds_combination_validator(odds_type: str) -> Callable:
        """オッズ組み合わせバリデーターを生成"""

        def validator(value: Any) -> Union[str, bool]:
            if not value:
                return "組み合わせが空です"

            parts = str(value).split("-")

            if odds_type in ["win", "place"]:
                if len(parts) != 1 or not parts[0].isdigit():
                    return f"{odds_type}の組み合わせは単一の馬番である必要があります"
            elif odds_type in ["exacta", "quinella", "wide"]:
                if len(parts) != 2:
                    return f"{odds_type}の組み合わせは2頭である必要があります"
                if not all(p.isdigit() for p in parts):
                    return "馬番は数字である必要があります"
                if parts[0] == parts[1]:
                    return "同じ馬番の組み合わせは無効です"
            elif odds_type in ["trio", "trifecta"]:
                if len(parts) != 3:
                    return f"{odds_type}の組み合わせは3頭である必要があります"
                if not all(p.isdigit() for p in parts):
                    return "馬番は数字である必要があります"
                if len(set(parts)) != 3:
                    return "重複する馬番は無効です"

            return True

        return validator

    @staticmethod
    def get_race_schema() -> Schema:
        """レース情報用スキーマを取得"""
        return Schema(
            "race",
            [
                SchemaField(
                    "race_key",
                    str,
                    required=True,
                    custom_validator=ValidationRules.jra_race_key_validator,
                ),
                SchemaField(
                    "race_date",
                    str,
                    required=True,
                    custom_validator=ValidationRules.japanese_date_validator,
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
                    "weather", str, enum_values=["晴", "曇", "雨", "小雨", "雪", None]
                ),
                SchemaField(
                    "track_condition",
                    str,
                    enum_values=["良", "稍重", "重", "不良", None],
                ),
                SchemaField(
                    "grade", str, enum_values=["G1", "G2", "G3", "OP", "L", None]
                ),
                SchemaField("prize_money_1st", int, min_value=0),
            ],
        )

    @staticmethod
    def get_horse_schema() -> Schema:
        """馬情報用スキーマを取得"""
        return Schema(
            "horse",
            [
                SchemaField("horse_key", str, required=True, pattern=r"^\d{8,}$"),
                SchemaField("name", str, required=True),
                SchemaField("sex", str, required=True, enum_values=["牡", "牝", "騸"]),
                SchemaField("age", int, required=True, min_value=1, max_value=30),
                SchemaField(
                    "birth_date",
                    str,
                    custom_validator=ValidationRules.japanese_date_validator,
                ),
                SchemaField(
                    "color",
                    str,
                    enum_values=[
                        "鹿毛",
                        "黒鹿毛",
                        "栗毛",
                        "栃栗毛",
                        "芦毛",
                        "白毛",
                        None,
                    ],
                ),
                SchemaField("sire_name", str),
                SchemaField("dam_name", str),
                SchemaField("breeder", str),
                SchemaField("owner", str),
                SchemaField("total_earnings", int, min_value=0),
            ],
        )

    @staticmethod
    def get_race_result_schema() -> Schema:
        """レース結果用スキーマを取得"""
        return Schema(
            "race_result",
            [
                SchemaField(
                    "race_key",
                    str,
                    required=True,
                    custom_validator=ValidationRules.jra_race_key_validator,
                ),
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
                SchemaField("bracket_number", int, min_value=1, max_value=8),
            ],
        )

    @staticmethod
    def get_odds_schema() -> Schema:
        """オッズ情報用スキーマを取得"""
        return Schema(
            "odds",
            [
                SchemaField(
                    "race_key",
                    str,
                    required=True,
                    custom_validator=ValidationRules.jra_race_key_validator,
                ),
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


class DataQualityRules:
    """データ品質ルール"""

    @staticmethod
    def check_completeness(
        data: Dict[str, Any], required_fields: List[str]
    ) -> Dict[str, float]:
        """
        データの完全性をチェック

        Args:
            data: チェック対象データ
            required_fields: 必須フィールドリスト

        Returns:
            完全性スコア
        """
        total_fields = len(data)
        filled_fields = sum(1 for v in data.values() if v is not None and v != "")
        required_filled = sum(
            1 for f in required_fields if data.get(f) is not None and data.get(f) != ""
        )

        return {
            "overall_completeness": filled_fields / total_fields
            if total_fields > 0
            else 0,
            "required_completeness": required_filled / len(required_fields)
            if required_fields
            else 1.0,
            "filled_fields": filled_fields,
            "total_fields": total_fields,
        }

    @staticmethod
    def check_consistency(data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        データの一貫性をチェック

        Args:
            data_list: チェック対象データリスト

        Returns:
            一貫性チェック結果
        """
        if not data_list:
            return {"is_consistent": True, "issues": []}

        issues = []

        # フィールド名の一貫性チェック
        field_sets = [set(data.keys()) for data in data_list]
        common_fields = set.intersection(*field_sets) if field_sets else set()
        all_fields = set.union(*field_sets) if field_sets else set()

        if common_fields != all_fields:
            missing_fields = all_fields - common_fields
            issues.append(f"一部のレコードでフィールドが欠落: {missing_fields}")

        return {
            "is_consistent": len(issues) == 0,
            "issues": issues,
            "common_fields": list(common_fields),
            "all_fields": list(all_fields),
        }
