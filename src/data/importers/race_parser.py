"""
レース情報CSVパーサー

TARGET frontier JVから出力されたレース情報CSVをパースし、
データベースに保存する機能を提供
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy.exc import IntegrityError

from src.core.exceptions import ValidationError
from src.core.logging import logger
from src.data.importers.base_parser import BaseCSVParser
from src.data.models.race import Race, Racecourse


class RaceCSVParser(BaseCSVParser):
    """レース情報CSVパーサー"""

    def _get_column_mappings(self) -> Dict[str, str]:
        """CSVカラムとDBカラムのマッピング"""
        return {
            "レースID": "race_key",
            "開催日": "race_date",
            "R": "race_number",
            "レース名": "race_name",
            "競馬場": "venue_name",
            "コース": "track_type",
            "距離": "distance",
            "クラス": "race_class",
            "天候": "weather",
            "馬場状態": "track_condition",
            "1着賞金": "prize_money_1st",
            "出走頭数": "entry_count",
            "グレード": "grade",
            "回り": "direction",
        }

    def _get_required_columns(self) -> List[str]:
        """必須カラムのリスト"""
        return ["レースID", "開催日", "R", "レース名", "競馬場", "コース", "距離"]

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
                "race_date": self._parse_date(row.get("race_date")),
                "race_number": self._parse_int(row.get("race_number")),
                "race_name": str(row.get("race_name", "")).strip(),
                "venue_name": self._normalize_venue(row.get("venue_name", "")),
                "race_type": self._normalize_track_type(row.get("track_type", "")),
                "distance": self._parse_int(row.get("distance")),
            }

            # オプション項目
            if pd.notna(row.get("race_class")):
                transformed["race_class"] = str(row["race_class"]).strip()

            if pd.notna(row.get("weather")):
                transformed["weather"] = self._normalize_weather(row["weather"])

            if pd.notna(row.get("track_condition")):
                transformed["track_condition"] = self._normalize_track_condition(
                    row["track_condition"]
                )

            if pd.notna(row.get("prize_money_1st")):
                transformed["prize_money_1st"] = self._parse_int(row["prize_money_1st"])

            if pd.notna(row.get("entry_count")):
                transformed["entry_count"] = self._parse_int(row["entry_count"])

            if pd.notna(row.get("grade")):
                transformed["grade"] = str(row["grade"]).strip()

            if pd.notna(row.get("direction")):
                transformed["direction"] = self._normalize_direction(row["direction"])

            return transformed

        except Exception as e:
            raise ValidationError(f"データ変換エラー: {e}") from e

    def _validate_row(self, row: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        レースデータのバリデーション

        Args:
            row: 変換後のデータ

        Returns:
            (バリデーション成功フラグ, エラーメッセージ)
        """
        # レースキーのフォーマットチェック(YYYYMMDDRRNN)
        race_key = row.get("race_key", "")
        if len(race_key) != 12 or not race_key.isdigit():
            return False, f"不正なレースIDフォーマット: {race_key}"

        # レース番号の範囲チェック
        race_number = row.get("race_number", 0)
        if not 1 <= race_number <= 12:
            return False, f"不正なレース番号: {race_number}"

        # 競馬場の存在確認
        venue_name = row.get("venue_name", "")
        if venue_name not in self._get_valid_venues():
            return False, f"不明な競馬場: {venue_name}"

        # 距離の妥当性チェック
        distance = row.get("distance", 0)
        if not 800 <= distance <= 3600:
            return False, f"不正な距離: {distance}m"

        # トラックタイプの確認
        race_type = row.get("race_type", "")
        if race_type not in ["芝", "ダート", "障害"]:
            return False, f"不正なトラックタイプ: {race_type}"

        return True, None

    def _save_row(self, row_data: Dict[str, Any]) -> bool:
        """
        レースデータを保存

        Args:
            row_data: 保存するデータ

        Returns:
            保存成功フラグ
        """
        try:
            # 競馬場IDの取得
            venue_name = row_data.pop("venue_name")
            racecourse = self._get_or_create_racecourse(venue_name)
            row_data["racecourse_id"] = racecourse.id

            # 既存レースのチェック
            existing = (
                self.db_session.query(Race)
                .filter_by(race_key=row_data["race_key"])
                .first()
            )

            if existing:
                # 更新
                for key, value in row_data.items():
                    setattr(existing, key, value)
                self.statistics["update_count"] += 1
                logger.debug(f"レース更新: {row_data['race_key']}")
            else:
                # 新規作成
                race = Race(**row_data)
                self.db_session.add(race)
                self.statistics["insert_count"] += 1
                logger.debug(f"レース作成: {row_data['race_key']}")

            return True

        except IntegrityError as e:
            logger.error(f"データベース整合性エラー: {e}")
            self.db_session.rollback()
            return False
        except Exception as e:
            logger.error(f"保存エラー: {e}")
            self.db_session.rollback()
            return False

    def _parse_date(self, date_str: Any) -> date:
        """日付文字列をパース"""
        if pd.isna(date_str):
            raise ValidationError("日付が空です")

        date_str = str(date_str).strip()

        # 複数の日付フォーマットに対応
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"]:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        raise ValidationError(f"日付の解析に失敗: {date_str}")

    def _parse_int(self, value: Any) -> int:
        """整数値をパース"""
        if pd.isna(value):
            raise ValidationError("数値が空です")

        # カンマ除去と変換
        if isinstance(value, str):
            value = value.replace(",", "").strip()

        return int(value)

    def _normalize_venue(self, venue: str) -> str:
        """競馬場名を正規化"""
        venue = str(venue).strip()

        venue_map = {
            "東京": "東京",
            "中山": "中山",
            "阪神": "阪神",
            "京都": "京都",
            "中京": "中京",
            "新潟": "新潟",
            "福島": "福島",
            "小倉": "小倉",
            "札幌": "札幌",
            "函館": "函館",
        }

        # 部分一致も考慮
        for key, value in venue_map.items():
            if key in venue:
                return value

        return venue

    def _normalize_track_type(self, track: str) -> str:
        """コース種別を正規化"""
        track = str(track).strip()

        if "芝" in track:
            return "芝"
        if "ダ" in track or "ダート" in track:
            return "ダート"
        if "障" in track or "障害" in track:
            return "障害"
        return track

    def _normalize_weather(self, weather: str) -> str:
        """天候を正規化"""
        weather = str(weather).strip()

        weather_map = {
            "晴": "晴",
            "曇": "曇",
            "雨": "雨",
            "小雨": "小雨",
            "雪": "雪",
            "小雪": "小雪",
        }

        # 部分一致
        for key, value in weather_map.items():
            if key in weather:
                return value

        return weather

    def _normalize_track_condition(self, condition: str) -> str:
        """馬場状態を正規化"""
        condition = str(condition).strip()

        condition_map = {
            "良": "良",
            "稍": "稍重",
            "稍重": "稍重",
            "重": "重",
            "不": "不良",
            "不良": "不良",
        }

        return condition_map.get(condition, condition)

    def _normalize_direction(self, direction: str) -> str:
        """回りを正規化"""
        direction = str(direction).strip()

        if "右" in direction:
            return "右"
        if "左" in direction:
            return "左"
        if "直" in direction:
            return "直線"
        return direction

    def _get_valid_venues(self) -> List[str]:
        """有効な競馬場名のリスト"""
        return [
            "東京",
            "中山",
            "阪神",
            "京都",
            "中京",
            "新潟",
            "福島",
            "小倉",
            "札幌",
            "函館",
        ]

    def _get_or_create_racecourse(self, venue_name: str) -> Racecourse:
        """競馬場を取得または作成"""
        # 既存の競馬場を検索
        racecourse = (
            self.db_session.query(Racecourse).filter_by(name=venue_name).first()
        )

        if not racecourse:
            # JRAコードのマッピング
            jra_code_map = {
                "札幌": "01",
                "函館": "02",
                "福島": "03",
                "新潟": "04",
                "東京": "05",
                "中山": "06",
                "中京": "07",
                "京都": "08",
                "阪神": "09",
                "小倉": "10",
            }

            jra_code = jra_code_map.get(venue_name, "99")

            # 新規作成
            racecourse = Racecourse(
                jra_code=jra_code,
                name=venue_name,
                name_kana=self._get_venue_kana(venue_name),
                location=self._get_venue_location(venue_name),
            )
            self.db_session.add(racecourse)
            self.db_session.flush()  # IDを取得するため

            logger.info(f"競馬場を作成: {venue_name}")

        return racecourse

    def _get_venue_kana(self, venue_name: str) -> str:
        """競馬場名のカナ表記を取得"""
        kana_map = {
            "札幌": "サッポロ",
            "函館": "ハコダテ",
            "福島": "フクシマ",
            "新潟": "ニイガタ",
            "東京": "トウキョウ",
            "中山": "ナカヤマ",
            "中京": "チュウキョウ",
            "京都": "キョウト",
            "阪神": "ハンシン",
            "小倉": "コクラ",
        }
        return kana_map.get(venue_name, venue_name)

    def _get_venue_location(self, venue_name: str) -> str:
        """競馬場の所在地を取得"""
        location_map = {
            "札幌": "北海道札幌市",
            "函館": "北海道函館市",
            "福島": "福島県福島市",
            "新潟": "新潟県新潟市",
            "東京": "東京都府中市",
            "中山": "千葉県船橋市",
            "中京": "愛知県豊明市",
            "京都": "京都府京都市",
            "阪神": "兵庫県宝塚市",
            "小倉": "福岡県北九州市",
        }
        return location_map.get(venue_name, "")
