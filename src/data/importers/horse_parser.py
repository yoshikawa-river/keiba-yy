"""
馬情報CSVパーサー

TARGET frontier JVから出力された馬情報CSVをパースし、
データベースに保存する機能を提供
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy.exc import IntegrityError

from src.core.exceptions import ValidationError
from src.core.logging import logger
from src.data.importers.base_parser import BaseCSVParser
from src.data.models.horse import Horse, Jockey, Trainer


class HorseCSVParser(BaseCSVParser):
    """馬情報CSVパーサー"""

    def _get_column_mappings(self) -> Dict[str, str]:
        """CSVカラムとDBカラムのマッピング"""
        return {
            "馬ID": "horse_key",
            "馬名": "name",
            "馬名欧字": "name_en",
            "性齢": "sex_age",
            "生年月日": "birth_date",
            "毛色": "color",
            "父馬": "sire_name",
            "母馬": "dam_name",
            "母父馬": "broodmare_sire_name",
            "生産者": "breeder",
            "馬主": "owner",
            "調教師": "trainer_name",
            "所属": "stable",
            "獲得賞金": "total_earnings",
            "通算成績": "career_record",
        }

    def _get_required_columns(self) -> List[str]:
        """必須カラムのリスト"""
        return ["馬ID", "馬名", "性齢"]

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
                "horse_key": str(row.get("horse_key", "")).strip(),
                "name": str(row.get("name", "")).strip(),
                "sex": self._extract_sex(row.get("sex_age", "")),
                "age": self._extract_age(row.get("sex_age", "")),
            }

            # オプション項目
            if pd.notna(row.get("name_en")):
                transformed["name_en"] = str(row["name_en"]).strip()

            if pd.notna(row.get("birth_date")):
                transformed["birth_date"] = self._parse_date(row["birth_date"])

            if pd.notna(row.get("color")):
                transformed["color"] = self._normalize_color(row["color"])

            if pd.notna(row.get("sire_name")):
                transformed["sire_name"] = str(row["sire_name"]).strip()

            if pd.notna(row.get("dam_name")):
                transformed["dam_name"] = str(row["dam_name"]).strip()

            if pd.notna(row.get("broodmare_sire_name")):
                transformed["broodmare_sire_name"] = str(
                    row["broodmare_sire_name"]
                ).strip()

            if pd.notna(row.get("breeder")):
                transformed["breeder"] = str(row["breeder"]).strip()

            if pd.notna(row.get("owner")):
                transformed["owner"] = str(row["owner"]).strip()

            if pd.notna(row.get("total_earnings")):
                transformed["total_earnings"] = self._parse_int(row["total_earnings"])

            if pd.notna(row.get("career_record")):
                transformed["career_record"] = str(row["career_record"]).strip()

            # 調教師情報
            if pd.notna(row.get("trainer_name")):
                transformed["trainer_info"] = {
                    "name": str(row["trainer_name"]).strip(),
                    "stable": str(row.get("stable", "")).strip(),
                }

            return transformed

        except Exception as e:
            raise ValidationError(f"データ変換エラー: {e}")

    def _validate_row(self, row: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        馬データのバリデーション

        Args:
            row: 変換後のデータ

        Returns:
            (バリデーション成功フラグ, エラーメッセージ)
        """
        # 馬キーのフォーマットチェック
        horse_key = row.get("horse_key", "")
        if len(horse_key) < 8 or not horse_key.isdigit():
            return False, f"不正な馬IDフォーマット: {horse_key}"

        # 性別チェック
        sex = row.get("sex", "")
        if sex not in ["牡", "牝", "騸"]:
            return False, f"不正な性別: {sex}"

        # 年齢チェック
        age = row.get("age", 0)
        if not 1 <= age <= 30:
            return False, f"不正な年齢: {age}"

        # 馬名チェック
        name = row.get("name", "")
        if not name or len(name) > 50:
            return False, f"不正な馬名: {name}"

        return True, None

    def _save_row(self, row_data: Dict[str, Any]) -> bool:
        """
        馬データを保存

        Args:
            row_data: 保存するデータ

        Returns:
            保存成功フラグ
        """
        try:
            # 調教師情報の処理
            trainer_info = row_data.pop("trainer_info", None)
            if trainer_info:
                trainer = self._get_or_create_trainer(
                    trainer_info["name"], trainer_info["stable"]
                )
                row_data["trainer_id"] = trainer.id

            # 既存馬のチェック
            existing = (
                self.db_session.query(Horse)
                .filter_by(horse_key=row_data["horse_key"])
                .first()
            )

            if existing:
                # 更新
                for key, value in row_data.items():
                    setattr(existing, key, value)
                self.statistics["update_count"] += 1
                logger.debug(
                    f"馬情報更新: {row_data['name']} ({row_data['horse_key']})"
                )
            else:
                # 新規作成
                horse = Horse(**row_data)
                self.db_session.add(horse)
                self.statistics["insert_count"] += 1
                logger.debug(
                    f"馬情報作成: {row_data['name']} ({row_data['horse_key']})"
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

    def _extract_sex(self, sex_age: str) -> str:
        """性齢から性別を抽出"""
        sex_age = str(sex_age).strip()
        if not sex_age:
            raise ValidationError("性齢が空です")

        # 最初の1文字が性別
        sex_char = sex_age[0]
        sex_map = {
            "牡": "牡",
            "牝": "牝",
            "騸": "騸",
            "セ": "騸",
        }

        if sex_char not in sex_map:
            raise ValidationError(f"不明な性別: {sex_char}")

        return sex_map[sex_char]

    def _extract_age(self, sex_age: str) -> int:
        """性齢から年齢を抽出"""
        sex_age = str(sex_age).strip()
        if not sex_age:
            raise ValidationError("性齢が空です")

        # 2文字目以降が年齢
        try:
            age_str = sex_age[1:]
            return int(age_str)
        except (IndexError, ValueError):
            raise ValidationError(f"年齢の抽出に失敗: {sex_age}")

    def _parse_date(self, date_str: Any) -> datetime.date:
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

        # カンマと万円単位の処理
        if isinstance(value, str):
            value = value.replace(",", "").replace("万円", "0000").strip()

        return int(value)

    def _normalize_color(self, color: str) -> str:
        """毛色を正規化"""
        color = str(color).strip()

        color_map = {
            "鹿毛": "鹿毛",
            "黒鹿毛": "黒鹿毛",
            "黒鹿": "黒鹿毛",
            "栗毛": "栗毛",
            "栃栗毛": "栃栗毛",
            "栃栗": "栃栗毛",
            "芦毛": "芦毛",
            "白毛": "白毛",
            "鹿": "鹿毛",
            "黒": "黒鹿毛",
            "栗": "栗毛",
            "栃": "栃栗毛",
            "芦": "芦毛",
            "白": "白毛",
        }

        # 完全一致を優先
        if color in color_map:
            return color_map[color]

        # 部分一致で検索（長い文字列から順に）
        sorted_keys = sorted(color_map.keys(), key=len, reverse=True)
        for key in sorted_keys:
            if key in color:
                return color_map[key]

        return color

    def _get_or_create_trainer(self, name: str, stable: str) -> Trainer:
        """調教師を取得または作成"""
        # 既存の調教師を検索
        trainer = self.db_session.query(Trainer).filter_by(name=name).first()

        if not trainer:
            # 新規作成
            trainer = Trainer(
                name=name,
                stable=stable,
                trainer_key=self._generate_trainer_key(name),
            )
            self.db_session.add(trainer)
            self.db_session.flush()  # IDを取得するため

            logger.info(f"調教師を作成: {name} ({stable})")

        return trainer

    def _generate_trainer_key(self, name: str) -> str:
        """
        調教師キーを生成

        実際のJRAキーがわからない場合の暫定処理
        """
        import hashlib

        # 名前のハッシュから8桁の数字を生成
        hash_obj = hashlib.md5(name.encode("utf-8"))
        hash_hex = hash_obj.hexdigest()
        # 16進数の最初の8文字を10進数に変換し、8桁にパディング
        trainer_key = str(int(hash_hex[:8], 16))[:8].zfill(8)

        return trainer_key
