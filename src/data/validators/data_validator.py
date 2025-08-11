from typing import Any, Optional

"""
データバリデーター

ビジネスロジックを含むデータ検証機能を提供
"""

from datetime import date, datetime

from sqlalchemy.orm import Session

from src.data.models.horse import Horse, Jockey, Trainer
from src.data.models.race import Race, Racecourse
from src.data.validators.base_validator import BaseValidator, ValidationResult


class DataValidator(BaseValidator):
    """データバリデーター(ビジネスロジック検証)"""

    def __init__(self, db_session: Session, strict_mode: bool = False):
        """
        データバリデーターの初期化

        Args:
            db_session: データベースセッション
            strict_mode: 厳格モード
        """
        super().__init__(strict_mode)
        self.db_session = db_session

    def validate(self, data: dict[str, Any]) -> ValidationResult:
        """
        データをバリデーション(汎用メソッド)

        Args:
            data: バリデーション対象データ

        Returns:
            バリデーション結果
        """
        # データタイプに応じて適切なバリデーションを実行
        if "race_key" in data and "race_name" in data:
            return self.validate_race(data)
        if "horse_key" in data and "name" in data and "sex" in data:
            return self.validate_horse(data)
        if "race_key" in data and "horse_key" in data and "jockey_key" in data:
            return self.validate_race_result(data)
        if "race_key" in data and "odds_type" in data:
            return self.validate_odds(data)
        result = ValidationResult(is_valid=False)
        result.add_error(
            field="data",
            value=data,
            message="データタイプを特定できません",
            error_type="unknown_data_type",
        )
        return result

    def validate_race(self, data: dict[str, Any]) -> ValidationResult:
        """
        レースデータのビジネスロジック検証

        Args:
            data: レースデータ

        Returns:
            バリデーション結果
        """
        result = ValidationResult(is_valid=True)

        # レースキーの重複チェック
        race_key = data.get("race_key")
        if race_key:
            existing_race = (
                self.db_session.query(Race).filter_by(race_key=race_key).first()
            )
            if existing_race:
                if self.strict_mode:
                    result.add_error(
                        field="race_key",
                        value=race_key,
                        message=f"レースキー '{race_key}' は既に存在します",
                        error_type="duplicate_key",
                    )
                else:
                    result.add_warning(
                        f"レースキー '{race_key}' は既に存在します(更新されます)"
                    )

        # 競馬場の存在チェック
        venue_name = data.get("venue_name")
        if venue_name:
            racecourse = (
                self.db_session.query(Racecourse).filter_by(name=venue_name).first()
            )
            if not racecourse:
                result.add_warning(
                    f"競馬場 '{venue_name}' がマスタに存在しません(自動作成されます)"
                )

        # 日付の論理チェック
        race_date_str = data.get("race_date")
        if race_date_str:
            try:
                race_date = datetime.strptime(race_date_str, "%Y-%m-%d").date()
                # 未来の日付チェック
                if race_date > date.today():
                    result.add_warning(f"レース日 '{race_date}' は未来の日付です")
                # 古すぎる日付チェック(1900年以前)
                if race_date.year < 1900:
                    result.add_error(
                        field="race_date",
                        value=race_date_str,
                        message=f"レース日 '{race_date}' は無効です(1900年以前)",
                        error_type="invalid_date",
                    )
            except ValueError:
                pass  # スキーマバリデーションで処理済み

        # グレードと賞金の整合性チェック
        grade = data.get("grade")
        prize_money_1st = data.get("prize_money_1st")
        if grade and prize_money_1st:
            min_prize = self._get_minimum_prize_for_grade(grade)
            if min_prize and prize_money_1st < min_prize:
                result.add_warning(
                    f"グレード '{grade}' のレースとしては賞金 {prize_money_1st:,}円 は少なすぎる可能性があります"
                )

        return result

    def validate_horse(self, data: dict[str, Any]) -> ValidationResult:
        """
        馬データのビジネスロジック検証

        Args:
            data: 馬データ

        Returns:
            バリデーション結果
        """
        result = ValidationResult(is_valid=True)

        # 馬キーの重複チェック
        horse_key = data.get("horse_key")
        if horse_key:
            existing_horse = (
                self.db_session.query(Horse).filter_by(horse_key=horse_key).first()
            )
            if existing_horse:
                if self.strict_mode:
                    result.add_error(
                        field="horse_key",
                        value=horse_key,
                        message=f"馬キー '{horse_key}' は既に存在します",
                        error_type="duplicate_key",
                    )
                else:
                    result.add_warning(
                        f"馬キー '{horse_key}' は既に存在します(更新されます)"
                    )

        # 年齢と生年月日の整合性チェック
        age = data.get("age")
        birth_date_str = data.get("birth_date")
        if age and birth_date_str:
            try:
                birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
                calculated_age = self._calculate_horse_age(birth_date)
                if abs(calculated_age - age) > 1:  # 1歳の誤差は許容
                    result.add_warning(
                        f"年齢 {age} と生年月日 {birth_date} が一致しません(計算上は {calculated_age} 歳)"
                    )
            except ValueError:
                pass

        # 調教師の存在チェック
        trainer_name = data.get("trainer_info", {}).get("name")
        if trainer_name:
            trainer = (
                self.db_session.query(Trainer).filter_by(name=trainer_name).first()
            )
            if not trainer:
                result.add_warning(
                    f"調教師 '{trainer_name}' がマスタに存在しません(自動作成されます)"
                )

        # 獲得賞金の妥当性チェック
        total_earnings = data.get("total_earnings")
        if total_earnings and total_earnings < 0:
            result.add_error(
                field="total_earnings",
                value=total_earnings,
                message="獲得賞金は負の値にできません",
                error_type="negative_value",
            )

        return result

    def validate_race_result(self, data: dict[str, Any]) -> ValidationResult:
        """
        レース結果データのビジネスロジック検証

        Args:
            data: レース結果データ

        Returns:
            バリデーション結果
        """
        result = ValidationResult(is_valid=True)

        # レースの存在チェック
        race_key = data.get("race_key")
        if race_key:
            race = self.db_session.query(Race).filter_by(race_key=race_key).first()
            if not race:
                result.add_error(
                    field="race_key",
                    value=race_key,
                    message=f"レース '{race_key}' が存在しません",
                    error_type="reference_not_found",
                )

        # 馬の存在チェック
        horse_key = data.get("horse_key")
        if horse_key:
            horse = self.db_session.query(Horse).filter_by(horse_key=horse_key).first()
            if not horse:
                result.add_warning(f"馬 '{horse_key}' が存在しません(自動作成されます)")

        # 騎手の存在チェック
        jockey_key = data.get("jockey_key")
        if jockey_key:
            jockey = (
                self.db_session.query(Jockey).filter_by(jockey_key=jockey_key).first()
            )
            if not jockey:
                result.add_warning(
                    f"騎手 '{jockey_key}' が存在しません(自動作成されます)"
                )

        # 着順とタイムの整合性チェック
        finish_position = data.get("result_data", {}).get("finish_position")
        finish_time = data.get("result_data", {}).get("finish_time")
        if finish_position and not finish_time:
            if finish_position <= 10:  # 上位10着はタイムが必須
                result.add_warning(
                    f"着順 {finish_position} ですがタイムが記録されていません"
                )

        # オッズと人気順の整合性チェック
        win_odds = data.get("result_data", {}).get("win_odds")
        favorite_order = data.get("result_data", {}).get("favorite_order")
        if win_odds and favorite_order:
            # 人気順が高いのにオッズが高すぎる場合
            if favorite_order <= 3 and win_odds > 10.0:
                result.add_warning(
                    f"{favorite_order}番人気でオッズ {win_odds} は高すぎる可能性があります"
                )

        return result

    def validate_odds(self, data: dict[str, Any]) -> ValidationResult:
        """
        オッズデータのビジネスロジック検証

        Args:
            data: オッズデータ

        Returns:
            バリデーション結果
        """
        result = ValidationResult(is_valid=True)

        # レースの存在チェック
        race_key = data.get("race_key")
        if race_key:
            race = self.db_session.query(Race).filter_by(race_key=race_key).first()
            if not race:
                result.add_error(
                    field="race_key",
                    value=race_key,
                    message=f"レース '{race_key}' が存在しません",
                    error_type="reference_not_found",
                )

        # 組み合わせの妥当性チェック
        odds_type = data.get("odds_type")
        combination = data.get("combination")
        if odds_type and combination:
            if not self._validate_odds_combination(odds_type, combination):
                result.add_error(
                    field="combination",
                    value=combination,
                    message=f"オッズタイプ '{odds_type}' に対して不正な組み合わせです",
                    error_type="invalid_combination",
                )

        # オッズ値の妥当性チェック
        odds_value = data.get("odds_value")
        if odds_value:
            # 単勝の場合の最低オッズチェック
            if odds_type == "win" and odds_value < 1.0:
                result.add_error(
                    field="odds_value",
                    value=odds_value,
                    message="単勝オッズは1.0倍以上である必要があります",
                    error_type="invalid_odds",
                )

        # 記録時刻の妥当性チェック
        recorded_at_str = data.get("recorded_at")
        if recorded_at_str and race:
            try:
                recorded_at = datetime.strptime(recorded_at_str, "%Y-%m-%d %H:%M:%S")

                # レース日より後の記録は無効
                if recorded_at.date() > race.race_date:
                    result.add_error(
                        field="recorded_at",
                        value=recorded_at_str,
                        message="オッズ記録時刻がレース日より後です",
                        error_type="invalid_timestamp",
                    )
            except ValueError:
                pass

        return result

    def _get_minimum_prize_for_grade(self, grade: str) -> Optional[int]:
        """グレードに応じた最低賞金を取得"""
        min_prizes = {
            "G1": 100000000,  # 1億円
            "G2": 50000000,  # 5千万円
            "G3": 30000000,  # 3千万円
            "OP": 10000000,  # 1千万円
            "L": 10000000,  # 1千万円
        }
        return min_prizes.get(grade)

    def _calculate_horse_age(self, birth_date: date) -> int:
        """馬の年齢を計算(日本の競馬では1月1日で歳を取る)"""
        today = date.today()
        # 競馬の年齢は生まれ年を0歳として、1月1日に一斉に歳を取る
        return today.year - birth_date.year

    def _validate_odds_combination(self, odds_type: str, combination: str) -> bool:
        """オッズの組み合わせを検証"""
        parts = combination.split("-")

        if odds_type in ["win", "place"]:
            return len(parts) == 1 and parts[0].isdigit()
        if odds_type in ["exacta", "quinella", "wide"]:
            return (
                len(parts) == 2
                and all(p.isdigit() for p in parts)
                and parts[0] != parts[1]
            )
        if odds_type in ["trio", "trifecta"]:
            return (
                len(parts) == 3
                and all(p.isdigit() for p in parts)
                and len(set(parts)) == 3
            )

        return False

    def validate_referential_integrity(
        self, data_type: str, data: dict[str, Any]
    ) -> ValidationResult:
        """
        参照整合性を検証

        Args:
            data_type: データタイプ
            data: データ

        Returns:
            バリデーション結果
        """
        result = ValidationResult(is_valid=True)

        if data_type == "race_result":
            # レース結果の参照整合性チェック
            race_key = data.get("race_key")
            horse_key = data.get("horse_key")
            jockey_key = data.get("jockey_key")

            if (
                race_key
                and not self.db_session.query(Race).filter_by(race_key=race_key).first()
            ):
                result.add_error(
                    field="race_key",
                    value=race_key,
                    message="参照先のレースが存在しません",
                    error_type="foreign_key_violation",
                )

            if (
                horse_key
                and not self.db_session.query(Horse)
                .filter_by(horse_key=horse_key)
                .first()
            ):
                result.add_error(
                    field="horse_key",
                    value=horse_key,
                    message="参照先の馬が存在しません",
                    error_type="foreign_key_violation",
                )

            if (
                jockey_key
                and not self.db_session.query(Jockey)
                .filter_by(jockey_key=jockey_key)
                .first()
            ):
                result.add_error(
                    field="jockey_key",
                    value=jockey_key,
                    message="参照先の騎手が存在しません",
                    error_type="foreign_key_violation",
                )

        return result
