"""
オッズCSVパーサー

TARGET frontier JVから出力されたオッズCSVをパースし、
データベースに保存する機能を提供
"""

from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy.exc import IntegrityError

from src.core.exceptions import ValidationError
from src.core.logging import logger
from src.data.importers.base_parser import BaseCSVParser
from src.data.models.odds import OddsHistory
from src.data.models.race import Race


class OddsCSVParser(BaseCSVParser):
    """オッズCSVパーサー"""

    def _get_column_mappings(self) -> dict[str, str]:
        """CSVカラムとDBカラムのマッピング"""
        return {
            "レースID": "race_key",
            "記録時刻": "recorded_at",
            "オッズ種別": "odds_type",
            "組み合わせ": "combination",
            "オッズ": "odds_value",
            "人気": "popularity",
            "票数": "vote_count",
            "支持率": "support_rate",
        }

    def _get_required_columns(self) -> list[str]:
        """必須カラムのリスト"""
        return ["レースID", "記録時刻", "オッズ種別", "組み合わせ", "オッズ"]

    def _transform_row(self, row: pd.Series) -> dict[str, Any]:
        """
        行データを変換

        Args:
            row: CSVの1行データ

        Returns:
            変換後のデータ

        Raises:
            ValidationError: データ変換エラー
        """
        try:
            # 基本変換
            transformed = {
                "race_key": str(row.get("race_key", "")).strip(),
                "recorded_at": self._parse_datetime(row.get("recorded_at")),
                "odds_type": self._normalize_odds_type(row.get("odds_type", "")),
                "combination": str(row.get("combination", "")).strip(),
                "odds_value": self._parse_float(row.get("odds_value")),
            }

            # オプション項目
            if pd.notna(row.get("popularity")):
                transformed["popularity"] = self._parse_int(row["popularity"])

            if pd.notna(row.get("vote_count")):
                transformed["vote_count"] = self._parse_int(row["vote_count"])

            if pd.notna(row.get("support_rate")):
                transformed["support_rate"] = self._parse_float(row["support_rate"])

            return transformed

        except Exception as e:
            raise ValidationError(f"データ変換エラー: {e}")

    def _validate_row(self, row: dict[str, Any]) -> tuple[bool, str | None]:
        """
        オッズデータのバリデーション

        Args:
            row: 変換後のデータ

        Returns:
            (バリデーション成功フラグ, エラーメッセージ)
        """
        # レースキーのフォーマットチェック
        race_key = row.get("race_key", "")
        if len(race_key) != 12 or not race_key.isdigit():
            return False, f"不正なレースIDフォーマット: {race_key}"

        # オッズ種別チェック
        odds_type = row.get("odds_type", "")
        valid_types = ["win", "place", "exacta", "quinella", "wide", "trio", "trifecta"]
        if odds_type not in valid_types:
            return False, f"不正なオッズ種別: {odds_type}"

        # 組み合わせフォーマットチェック
        combination = row.get("combination", "")
        if not self._validate_combination(odds_type, combination):
            return False, f"不正な組み合わせフォーマット: {odds_type} - {combination}"

        # オッズ値チェック
        odds_value = row.get("odds_value", 0)
        if odds_value < 1.0:
            return False, f"不正なオッズ値: {odds_value}"

        # 人気順チェック（存在する場合）
        popularity = row.get("popularity")
        if popularity is not None and popularity < 1:
            return False, f"不正な人気順: {popularity}"

        # 支持率チェック（存在する場合）
        support_rate = row.get("support_rate")
        if support_rate is not None and not 0 <= support_rate <= 100:
            return False, f"不正な支持率: {support_rate}"

        return True, None

    def _save_row(self, row_data: dict[str, Any]) -> bool:
        """
        オッズデータを保存

        Args:
            row_data: 保存するデータ

        Returns:
            保存成功フラグ
        """
        try:
            # レースの存在確認
            race = (
                self.db_session.query(Race)
                .filter_by(race_key=row_data["race_key"])
                .first()
            )
            if not race:
                self._add_warning(
                    -1,
                    f"レースが見つかりません: {row_data['race_key']}",
                    row_data,
                )
                return False

            # race_keyをrace_idに変換
            row_data["race_id"] = race.id
            del row_data["race_key"]

            # 既存オッズのチェック（同一時刻・種別・組み合わせ）
            existing = (
                self.db_session.query(OddsHistory)
                .filter_by(
                    race_id=row_data["race_id"],
                    recorded_at=row_data["recorded_at"],
                    odds_type=row_data["odds_type"],
                    combination=row_data["combination"],
                )
                .first()
            )

            if existing:
                # 更新
                for key, value in row_data.items():
                    setattr(existing, key, value)
                self.statistics["update_count"] += 1
                logger.debug(
                    f"オッズ更新: {row_data['odds_type']} - {row_data['combination']}"
                )
            else:
                # 新規作成
                odds = OddsHistory(**row_data)
                self.db_session.add(odds)
                self.statistics["insert_count"] += 1
                logger.debug(
                    f"オッズ作成: {row_data['odds_type']} - {row_data['combination']}"
                )

            return True

        except IntegrityError as e:
            logger.error(f"データベース整合性エラー: {e}")
            self.db_session.rollback()
            return False
        except Exception as e:
            logger.error(f"保存エラー: {e}")
            self.db_session.rollback()
            return False

    def _parse_datetime(self, datetime_str: Any) -> datetime:
        """日時文字列をパース"""
        if pd.isna(datetime_str):
            raise ValidationError("日時が空です")

        datetime_str = str(datetime_str).strip()

        # 複数の日時フォーマットに対応
        for fmt in [
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y年%m月%d日 %H時%M分%S秒",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M",
        ]:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue

        raise ValidationError(f"日時の解析に失敗: {datetime_str}")

    def _parse_int(self, value: Any) -> int:
        """整数値をパース"""
        if pd.isna(value):
            raise ValidationError("数値が空です")

        # カンマ除去と変換
        if isinstance(value, str):
            value = value.replace(",", "").strip()

        return int(value)

    def _parse_float(self, value: Any) -> float:
        """浮動小数点数をパース"""
        if pd.isna(value):
            raise ValidationError("数値が空です")

        # カンマ除去と変換
        if isinstance(value, str):
            value = value.replace(",", "").strip()

        return float(value)

    def _normalize_odds_type(self, odds_type: str) -> str:
        """オッズ種別を正規化"""
        odds_type = str(odds_type).strip()

        type_map = {
            "単勝": "win",
            "複勝": "place",
            "馬連": "exacta",
            "馬単": "quinella",
            "ワイド": "wide",
            "3連複": "trio",
            "3連単": "trifecta",
            "WIN": "win",
            "PLACE": "place",
            "EXACTA": "exacta",
            "QUINELLA": "quinella",
            "WIDE": "wide",
            "TRIO": "trio",
            "TRIFECTA": "trifecta",
        }

        return type_map.get(odds_type, odds_type.lower())

    def _validate_combination(self, odds_type: str, combination: str) -> bool:
        """
        組み合わせフォーマットのバリデーション

        Args:
            odds_type: オッズ種別
            combination: 組み合わせ文字列

        Returns:
            バリデーション成功フラグ
        """
        # ハイフン区切りのフォーマットチェック
        parts = combination.split("-")

        if odds_type == "win":
            # 単勝: 馬番1つ（例: "3"）
            return len(parts) == 1 and parts[0].isdigit()

        if odds_type == "place":
            # 複勝: 馬番1つ（例: "5"）
            return len(parts) == 1 and parts[0].isdigit()

        if odds_type in ["exacta", "quinella"]:
            # 馬連・馬単: 馬番2つ（例: "3-5"）
            return (
                len(parts) == 2
                and all(p.isdigit() for p in parts)
                and parts[0] != parts[1]
            )

        if odds_type == "wide":
            # ワイド: 馬番2つ（例: "3-5"）
            return (
                len(parts) == 2
                and all(p.isdigit() for p in parts)
                and parts[0] != parts[1]
            )

        if odds_type == "trio":
            # 3連複: 馬番3つ（例: "3-5-7"）
            return (
                len(parts) == 3
                and all(p.isdigit() for p in parts)
                and len(set(parts)) == 3  # 重複なし
            )

        if odds_type == "trifecta":
            # 3連単: 馬番3つ（例: "3-5-7"）
            return (
                len(parts) == 3
                and all(p.isdigit() for p in parts)
                and len(set(parts)) == 3  # 重複なし
            )

        return False
