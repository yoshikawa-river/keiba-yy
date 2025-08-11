from typing import Any

import pandas as pd
from loguru import logger

"""レース条件特徴量抽出モジュール

レース条件（距離、クラス、頭数、開催時期など）に関する特徴量を生成する。
基本的なレース条件特徴量15個を実装。
"""


class FeatureExtractionError(Exception):
    """特徴量抽出エラー"""

    pass


class RaceConditionExtractor:
    """レース条件特徴量を抽出するクラス

    Phase1のレース条件特徴量15個を実装。
    距離、クラス、頭数、競馬場、開催時期などの特徴量を計算。
    """

    def __init__(self):
        """初期化"""
        self.feature_names = []
        self.feature_count = 0

        # レースクラスの階級定義
        self.class_ranks = {
            "G1": 10,
            "G2": 9,
            "G3": 8,
            "オープン": 7,
            "3勝": 6,
            "2勝": 5,
            "1勝": 4,
            "新馬": 3,
            "未勝利": 2,
            "その他": 1,
        }

        # 競馬場の特性（左回り/右回り、規模）
        self.track_characteristics = {
            "東京": {"turn": "left", "scale": "large"},
            "中山": {"turn": "right", "scale": "medium"},
            "京都": {"turn": "right", "scale": "large"},
            "阪神": {"turn": "right", "scale": "large"},
            "中京": {"turn": "left", "scale": "medium"},
            "新潟": {"turn": "left", "scale": "small"},
            "福島": {"turn": "right", "scale": "small"},
            "札幌": {"turn": "right", "scale": "small"},
            "函館": {"turn": "right", "scale": "small"},
            "小倉": {"turn": "right", "scale": "small"},
        }

    def extract_basic_race_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """基本レース条件特徴量（8個）

        Args:
            df: レースデータ

        Returns:
            特徴量を追加したデータフレーム
        """
        logger.info("基本レース条件特徴量の抽出開始")
        df_features = df.copy()

        # 1. 距離カテゴリ（スプリント/マイル/中距離/長距離）
        if "distance" in df.columns:
            df_features["distance_category"] = pd.cut(
                df["distance"],
                bins=[0, 1400, 1800, 2200, 4000],
                labels=[0, 1, 2, 3],  # sprint, mile, intermediate, long
            ).astype(float)

            # 2. 距離の正規化（1000-3600m → 0-1）
            df_features["distance_normalized"] = (df["distance"] - 1000) / 2600

            # 3. 距離二乗項（非線形性を捉える）
            df_features["distance_squared"] = (df["distance"] / 1000) ** 2

        # 4. レースクラスランク
        if "race_class" in df.columns:
            df_features["class_rank"] = df["race_class"].map(self.class_ranks).fillna(1)

            # 5. 高グレードレースフラグ（G1-G3）
            df_features["is_graded_race"] = (
                df["race_class"].isin(["G1", "G2", "G3"]).astype(float)
            )

        # 6. 出走頭数
        if "field_size" in df.columns:
            df_features["field_size_normalized"] = df["field_size"] / 18  # 最大18頭

            # 7. 多頭数レースフラグ（15頭以上）
            df_features["is_large_field"] = (df["field_size"] >= 15).astype(float)

            # 8. 少頭数レースフラグ（8頭以下）
            df_features["is_small_field"] = (df["field_size"] <= 8).astype(float)

        # デフォルト値の設定
        basic_features = [
            "distance_category",
            "distance_normalized",
            "distance_squared",
            "class_rank",
            "is_graded_race",
            "field_size_normalized",
            "is_large_field",
            "is_small_field",
        ]

        for feat in basic_features:
            if feat not in df_features.columns:
                df_features[feat] = 0
            else:
                df_features[feat] = df_features[feat].fillna(0)

        self.feature_names.extend(basic_features)
        self.feature_count += 8
        logger.info("基本レース条件特徴量8個を追加")

        return df_features

    def extract_track_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """競馬場・コース特徴量（7個）

        Args:
            df: レースデータ

        Returns:
            特徴量を追加したデータフレーム
        """
        logger.info("競馬場・コース特徴量の抽出開始")
        df_features = df.copy()

        # 1. 競馬場カテゴリ（エンコーディング）
        if "venue" in df.columns:
            venue_mapping = {
                "東京": 1,
                "中山": 2,
                "京都": 3,
                "阪神": 4,
                "中京": 5,
                "新潟": 6,
                "福島": 7,
                "札幌": 8,
                "函館": 9,
                "小倉": 10,
            }
            df_features["venue_encoded"] = df["venue"].map(venue_mapping).fillna(0)

            # 2. 左回り/右回りフラグ
            df_features["is_left_turn"] = df["venue"].apply(
                lambda x: 1
                if self.track_characteristics.get(x, {}).get("turn") == "left"
                else 0
            )

            # 3. 大規模競馬場フラグ
            df_features["is_large_track"] = df["venue"].apply(
                lambda x: 1
                if self.track_characteristics.get(x, {}).get("scale") == "large"
                else 0
            )

            # 4. ローカル競馬場フラグ（小規模）
            df_features["is_local_track"] = df["venue"].apply(
                lambda x: 1
                if self.track_characteristics.get(x, {}).get("scale") == "small"
                else 0
            )

        # 5. 芝/ダート/障害フラグ
        if "track_type" in df.columns:
            df_features["is_turf"] = (df["track_type"] == "turf").astype(float)
            df_features["is_dirt"] = (df["track_type"] == "dirt").astype(float)

        # 6. 馬場状態エンコーディング
        if "track_condition" in df.columns:
            condition_mapping = {
                "firm": 1,  # 良
                "good": 1,  # 良
                "yielding": 2,  # 稍重
                "soft": 3,  # 重
                "heavy": 4,  # 不良
            }
            df_features["track_condition_encoded"] = (
                df["track_condition"].map(condition_mapping).fillna(1)
            )

        # デフォルト値の設定
        track_features = [
            "venue_encoded",
            "is_left_turn",
            "is_large_track",
            "is_local_track",
            "is_turf",
            "is_dirt",
            "track_condition_encoded",
        ]

        for feat in track_features:
            if feat not in df_features.columns:
                df_features[feat] = 0
            else:
                df_features[feat] = df_features[feat].fillna(0)

        self.feature_names.extend(track_features)
        self.feature_count += 7
        logger.info("競馬場・コース特徴量7個を追加")

        return df_features

    def extract_all_race_condition_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """全レース条件特徴量を抽出（15個）

        Args:
            df: レースデータ

        Returns:
            全特徴量を追加したデータフレーム
        """
        logger.info("========== レース条件特徴量抽出開始 ==========")

        try:
            # 基本レース条件特徴量（8個）
            df_features = self.extract_basic_race_features(df)

            # 競馬場・コース特徴量（7個）
            df_features = self.extract_track_features(df_features)

            logger.info(f"✅ レース条件特徴量抽出完了: 合計{self.feature_count}個の特徴量を生成")
            logger.info(f"生成された特徴量: {self.feature_names}")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(f"レース条件特徴量抽出中にエラーが発生しました: {e!s}") from e

    def get_feature_info(self) -> dict[str, Any]:
        """特徴量情報の取得

        Returns:
            特徴量の情報辞書
        """
        return {
            "feature_names": self.feature_names,
            "feature_count": self.feature_count,
            "categories": {
                "basic_race": 8,
                "track": 7,
            },
        }
