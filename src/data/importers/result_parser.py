"""
レース結果CSVパーサー

TARGET frontier JVから出力されたレース結果CSVをパースし、
データベースに保存する機能を提供
"""

from datetime import datetime, time
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy.exc import IntegrityError

from src.core.exceptions import ValidationError
from src.core.logging import logger
from src.data.importers.base_parser import BaseCSVParser
from src.data.models.horse import Horse, Jockey
from src.data.models.race import Race
from src.data.models.result import RaceEntry, RaceResult


class ResultCSVParser(BaseCSVParser):
    """レース結果CSVパーサー"""

    def _get_column_mappings(self) -> Dict[str, str]:
        """CSVカラムとDBカラムのマッピング"""
        return {
            "レースID": "race_key",
            "馬番": "post_position",
            "枠番": "bracket_number",
            "馬ID": "horse_key",
            "馬名": "horse_name",
            "騎手ID": "jockey_key",
            "騎手名": "jockey_name",
            "斤量": "weight_carried",
            "着順": "finish_position",
            "タイム": "finish_time",
            "着差": "margin",
            "通過順": "position_at_corners",
            "上り": "final_furlong_time",
            "単勝オッズ": "win_odds",
            "人気": "favorite_order",
            "馬体重": "horse_weight",
            "増減": "weight_change",
            "コメント": "comment",
        }

    def _get_required_columns(self) -> List[str]:
        """必須カラムのリスト"""
        return ["レースID", "馬番", "馬ID", "騎手ID", "斤量"]

    def _transform_row(self, row: pd.Series) -> Dict[str, Any]:
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
                "post_position": self._parse_int(row.get("post_position")),
                "horse_key": str(row.get("horse_key", "")).strip(),
                "jockey_key": str(row.get("jockey_key", "")).strip(),
                "weight_carried": self._parse_float(row.get("weight_carried")),
            }

            # オプション項目（エントリー情報）
            if pd.notna(row.get("bracket_number")):
                transformed["bracket_number"] = self._parse_int(row["bracket_number"])

            # 結果情報
            result_data = {}

            if pd.notna(row.get("finish_position")):
                finish_pos = self._parse_finish_position(row["finish_position"])
                if finish_pos:
                    result_data["finish_position"] = finish_pos

            if pd.notna(row.get("finish_time")):
                result_data["finish_time"] = self._parse_time(row["finish_time"])  # type: ignore

            if pd.notna(row.get("margin")):
                result_data["margin"] = self._parse_margin(row["margin"])  # type: ignore

            if pd.notna(row.get("position_at_corners")):
                result_data["position_at_corners"] = str(
                    row["position_at_corners"]
                ).strip()  # type: ignore

            if pd.notna(row.get("final_furlong_time")):
                result_data["final_furlong_time"] = self._parse_float(
                    row["final_furlong_time"]
                )  # type: ignore

            if pd.notna(row.get("win_odds")):
                result_data["win_odds"] = self._parse_float(row["win_odds"])  # type: ignore

            if pd.notna(row.get("favorite_order")):
                result_data["favorite_order"] = self._parse_int(row["favorite_order"])  # type: ignore

            if pd.notna(row.get("horse_weight")):
                result_data["horse_weight"] = self._parse_int(row["horse_weight"])  # type: ignore

            if pd.notna(row.get("weight_change")):
                result_data["weight_change"] = self._parse_weight_change(
                    row["weight_change"]
                )  # type: ignore

            if pd.notna(row.get("comment")):
                result_data["comment"] = str(row["comment"]).strip()  # type: ignore

            transformed["result_data"] = result_data if result_data else None

            # 参照用の名前情報
            if pd.notna(row.get("horse_name")):
                transformed["horse_name"] = str(row["horse_name"]).strip()
            if pd.notna(row.get("jockey_name")):
                transformed["jockey_name"] = str(row["jockey_name"]).strip()

            return transformed

        except Exception as e:
            raise ValidationError(f"データ変換エラー: {e}")

    def _validate_row(self, row: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        レース結果データのバリデーション

        Args:
            row: 変換後のデータ

        Returns:
            (バリデーション成功フラグ, エラーメッセージ)
        """
        # レースキーのフォーマットチェック
        race_key = row.get("race_key", "")
        if len(race_key) != 12 or not race_key.isdigit():
            return False, f"不正なレースIDフォーマット: {race_key}"

        # 馬番の範囲チェック
        post_position = row.get("post_position", 0)
        if not 1 <= post_position <= 28:
            return False, f"不正な馬番: {post_position}"

        # 馬キーのフォーマットチェック
        horse_key = row.get("horse_key", "")
        if len(horse_key) < 8 or not horse_key.isdigit():
            return False, f"不正な馬IDフォーマット: {horse_key}"

        # 騎手キーのフォーマットチェック
        jockey_key = row.get("jockey_key", "")
        if len(jockey_key) < 4 or not jockey_key.isdigit():
            return False, f"不正な騎手IDフォーマット: {jockey_key}"

        # 斤量チェック
        weight_carried = row.get("weight_carried", 0)
        if not 48.0 <= weight_carried <= 65.0:
            return False, f"不正な斤量: {weight_carried}"

        return True, None

    def _save_row(self, row_data: Dict[str, Any]) -> bool:
        """
        レース結果データを保存

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

            # 馬の存在確認
            horse = (
                self.db_session.query(Horse)
                .filter_by(horse_key=row_data["horse_key"])
                .first()
            )
            if not horse:
                # 馬が存在しない場合は作成（最小限の情報で）
                horse_name = row_data.get(
                    "horse_name", f"Unknown_{row_data['horse_key']}"
                )
                horse = Horse(
                    horse_key=row_data["horse_key"],
                    name=horse_name,
                    sex="不明",
                    age=0,
                )
                self.db_session.add(horse)
                self.db_session.flush()
                logger.warning(f"馬を仮作成: {horse_name} ({row_data['horse_key']})")

            # 騎手の存在確認または作成
            jockey = self._get_or_create_jockey(
                row_data["jockey_key"],
                row_data.get("jockey_name", f"Unknown_{row_data['jockey_key']}"),
            )

            # エントリー情報の保存または更新
            entry = (
                self.db_session.query(RaceEntry)
                .filter_by(
                    race_id=race.id,
                    horse_id=horse.id,
                )
                .first()
            )

            entry_data = {
                "race_id": race.id,
                "horse_id": horse.id,
                "jockey_id": jockey.id,
                "post_position": row_data["post_position"],
                "bracket_number": row_data.get("bracket_number"),
                "weight_carried": row_data["weight_carried"],
            }

            if entry:
                # 更新
                for key, value in entry_data.items():
                    setattr(entry, key, value)
            else:
                # 新規作成
                entry = RaceEntry(**entry_data)
                self.db_session.add(entry)
                self.db_session.flush()

            # 結果情報の保存（存在する場合）
            result_data = row_data.get("result_data")
            if result_data:
                result = (
                    self.db_session.query(RaceResult)
                    .filter_by(race_entry_id=entry.id)
                    .first()
                )

                result_data["race_entry_id"] = entry.id

                if result:
                    # 更新
                    for key, value in result_data.items():
                        setattr(result, key, value)
                    self.statistics["update_count"] += 1
                else:
                    # 新規作成
                    result = RaceResult(**result_data)
                    self.db_session.add(result)
                    self.statistics["insert_count"] += 1

            return True

        except IntegrityError as e:
            logger.error(f"データベース整合性エラー: {e}")
            self.db_session.rollback()
            return False
        except Exception as e:
            logger.error(f"保存エラー: {e}")
            self.db_session.rollback()
            return False

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

    def _parse_finish_position(self, position: Any) -> Optional[int]:
        """着順をパース（中止・除外等に対応）"""
        if pd.isna(position):
            return None

        position = str(position).strip()

        # 数字の場合
        if position.isdigit():
            return int(position)

        # 特殊ケース
        special_cases = {
            "中止": None,
            "除外": None,
            "取消": None,
            "失格": None,
            "降着": None,  # 降着は別途処理が必要
        }

        return special_cases.get(position, None)

    def _parse_time(self, time_str: Any) -> Optional[time]:
        """タイムをパース（分:秒.ミリ秒形式）"""
        if pd.isna(time_str):
            return None

        time_str = str(time_str).strip()

        try:
            # 分:秒.ミリ秒 形式（例: 1:23.4）
            if ":" in time_str:
                parts = time_str.split(":")
                minutes = int(parts[0])
                seconds_parts = parts[1].split(".")
                seconds = int(seconds_parts[0])
                milliseconds = (
                    int(seconds_parts[1]) * 100 if len(seconds_parts) > 1 else 0
                )

                return time(0, minutes, seconds, milliseconds * 1000)
            # 秒.ミリ秒 形式（例: 83.4）
            else:
                parts = time_str.split(".")
                total_seconds = int(parts[0])
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                milliseconds = int(parts[1]) * 100 if len(parts) > 1 else 0

                return time(0, minutes, seconds, milliseconds * 1000)
        except Exception:
            return None

    def _parse_margin(self, margin: Any) -> Optional[str]:
        """着差をパース"""
        if pd.isna(margin):
            return None

        margin = str(margin).strip()

        # 特殊表記の正規化
        margin_map = {
            "ハナ": "ハナ",
            "アタマ": "アタマ",
            "クビ": "クビ",
            "1/2": "1/2",
            "3/4": "3/4",
            "1.1/4": "1.1/4",
            "1.1/2": "1.1/2",
            "1.3/4": "1.3/4",
            "2.1/2": "2.1/2",
            "大": "大差",
        }

        # マッピングにあればそれを返す
        for key, value in margin_map.items():
            if key in margin:
                return value

        # 数字のみの場合（馬身数）
        if margin.replace(".", "").isdigit():
            return str(margin)

        return str(margin)

    def _parse_weight_change(self, change: Any) -> Optional[int]:
        """体重増減をパース"""
        if pd.isna(change):
            return None

        change = str(change).strip()

        # プラスマイナスの処理
        if change.startswith("+"):
            return int(change[1:])
        elif change.startswith("-"):
            return -int(change[1:])
        else:
            return int(change)

    def _get_or_create_jockey(self, jockey_key: str, name: str) -> Jockey:
        """騎手を取得または作成"""
        # 既存の騎手を検索
        jockey = self.db_session.query(Jockey).filter_by(jockey_key=jockey_key).first()

        if not jockey:
            # 新規作成
            jockey = Jockey(
                jockey_key=jockey_key,
                name=name,
            )
            self.db_session.add(jockey)
            self.db_session.flush()  # IDを取得するため

            logger.info(f"騎手を作成: {name} ({jockey_key})")

        return jockey
