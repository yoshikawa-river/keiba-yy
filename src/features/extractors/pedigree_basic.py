from typing import Any, Optional

import numpy as np
import pandas as pd
from loguru import logger

"""血統基本特徴量抽出モジュール

父、母父、系統などの基本的な血統情報から特徴量を生成する。
Phase1の血統基本特徴量15個を実装。
"""


class FeatureExtractionError(Exception):
    """特徴量抽出エラー"""

    pass


class PedigreeBasicExtractor:
    """血統基本特徴量を抽出するクラス

    Phase1の血統基本特徴量15個を実装。
    父系、母系、系統、血統相性などの基本的な特徴量を計算。
    """

    def __init__(self):
        """初期化"""
        self.feature_names = []
        self.feature_count = 0

        # 主要系統の定義
        self.major_bloodlines = {
            # 父系主要系統
            "Sunday Silence": "sunday",
            "Deep Impact": "sunday",
            "Heart's Cry": "sunday",
            "King Kamehameha": "kingmambo",
            "Lord Kanaloa": "kingmambo",
            "Rulership": "kingmambo",
            "Daiwa Major": "sunday",
            "Stay Gold": "sunday",
            "Orfevre": "sunday",
            "Epiphaneia": "roberto",
            "Kizuna": "sunday",
            "Gold Ship": "sunday",
            # ノーザンダンサー系
            "Northern Dancer": "northern",
            "Danzig": "northern",
            "Storm Cat": "northern",
            # その他の主要系統
            "Mr. Prospector": "prospector",
            "Bold Ruler": "bold",
            "Native Dancer": "native",
        }

        # 距離適性による血統分類
        self.distance_aptitude = {
            "sprint": ["Sakura Bakushin O", "Lord Kanaloa", "Daiwa Major"],
            "mile": ["Deep Impact", "Daiwa Major", "King Kamehameha"],
            "intermediate": ["Deep Impact", "Heart's Cry", "Stay Gold"],
            "long": ["Stay Gold", "Orfevre", "Gold Ship"],
        }

    def extract_sire_features(
        self, df: pd.DataFrame, pedigree_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """父系特徴量（5個）

        Args:
            df: レースデータ
            pedigree_df: 血統データ

        Returns:
            特徴量を追加したデータフレーム
        """
        logger.info("父系特徴量の抽出開始")
        df_features = df.copy()

        if pedigree_df is not None and "horse_id" in df.columns:
            for horse_id in df["horse_id"].unique():
                horse_pedigree = pedigree_df[pedigree_df["horse_id"] == horse_id]

                if len(horse_pedigree) > 0:
                    # 1. 父のID（エンコーディング）
                    if "sire_id" in horse_pedigree.columns:
                        sire_id = horse_pedigree.iloc[0]["sire_id"]
                        # 簡易的なハッシュ値でエンコーディング
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "sire_encoded"
                        ] = hash(str(sire_id)) % 10000

                    # 2. 父の系統
                    if "sire_name" in horse_pedigree.columns:
                        sire_name = horse_pedigree.iloc[0]["sire_name"]
                        bloodline = self.major_bloodlines.get(sire_name, "other")
                        bloodline_map = {
                            "sunday": 1,
                            "kingmambo": 2,
                            "northern": 3,
                            "prospector": 4,
                            "bold": 5,
                            "native": 6,
                            "roberto": 7,
                            "other": 0,
                        }
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "sire_bloodline"
                        ] = bloodline_map[bloodline]

                    # 3. 父の産駒勝率（統計データがある場合）
                    if "sire_win_rate" in horse_pedigree.columns:
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "sire_win_rate"
                        ] = horse_pedigree.iloc[0]["sire_win_rate"]

                    # 4. 父の産駒複勝率
                    if "sire_place_rate" in horse_pedigree.columns:
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "sire_place_rate"
                        ] = horse_pedigree.iloc[0]["sire_place_rate"]

                    # 5. 父の産駒平均賞金（対数変換）
                    if "sire_avg_earnings" in horse_pedigree.columns:
                        avg_earnings = horse_pedigree.iloc[0]["sire_avg_earnings"]
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "sire_earnings_log"
                        ] = np.log1p(avg_earnings)

        # デフォルト値の設定
        sire_features = [
            "sire_encoded",
            "sire_bloodline",
            "sire_win_rate",
            "sire_place_rate",
            "sire_earnings_log",
        ]

        for feat in sire_features:
            if feat not in df_features.columns:
                df_features[feat] = 0
            else:
                df_features[feat] = df_features[feat].fillna(0)

        self.feature_names.extend(sire_features)
        self.feature_count += 5
        logger.info("父系特徴量5個を追加")

        return df_features

    def extract_dam_sire_features(
        self, df: pd.DataFrame, pedigree_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """母父系特徴量（5個）

        Args:
            df: レースデータ
            pedigree_df: 血統データ

        Returns:
            特徴量を追加したデータフレーム
        """
        logger.info("母父系特徴量の抽出開始")
        df_features = df.copy()

        if pedigree_df is not None and "horse_id" in df.columns:
            for horse_id in df["horse_id"].unique():
                horse_pedigree = pedigree_df[pedigree_df["horse_id"] == horse_id]

                if len(horse_pedigree) > 0:
                    # 1. 母父のID（エンコーディング）
                    if "dam_sire_id" in horse_pedigree.columns:
                        dam_sire_id = horse_pedigree.iloc[0]["dam_sire_id"]
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "dam_sire_encoded"
                        ] = hash(str(dam_sire_id)) % 10000

                    # 2. 母父の系統
                    if "dam_sire_name" in horse_pedigree.columns:
                        dam_sire_name = horse_pedigree.iloc[0]["dam_sire_name"]
                        bloodline = self.major_bloodlines.get(dam_sire_name, "other")
                        bloodline_map = {
                            "sunday": 1,
                            "kingmambo": 2,
                            "northern": 3,
                            "prospector": 4,
                            "bold": 5,
                            "native": 6,
                            "roberto": 7,
                            "other": 0,
                        }
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "dam_sire_bloodline"
                        ] = bloodline_map[bloodline]

                    # 3. 母父の産駒勝率
                    if "dam_sire_win_rate" in horse_pedigree.columns:
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "dam_sire_win_rate"
                        ] = horse_pedigree.iloc[0]["dam_sire_win_rate"]

                    # 4. 母父の産駒複勝率
                    if "dam_sire_place_rate" in horse_pedigree.columns:
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "dam_sire_place_rate"
                        ] = horse_pedigree.iloc[0]["dam_sire_place_rate"]

                    # 5. 母系の活力指標（母の産駒数や成績）
                    if "dam_progeny_count" in horse_pedigree.columns:
                        progeny_count = horse_pedigree.iloc[0]["dam_progeny_count"]
                        # 産駒数を正規化（1-10頭を0-1にマッピング）
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "dam_vitality"
                        ] = min(progeny_count / 10, 1.0)

        # デフォルト値の設定
        dam_sire_features = [
            "dam_sire_encoded",
            "dam_sire_bloodline",
            "dam_sire_win_rate",
            "dam_sire_place_rate",
            "dam_vitality",
        ]

        for feat in dam_sire_features:
            if feat not in df_features.columns:
                df_features[feat] = 0
            else:
                df_features[feat] = df_features[feat].fillna(0)

        self.feature_names.extend(dam_sire_features)
        self.feature_count += 5
        logger.info("母父系特徴量5個を追加")

        return df_features

    def extract_bloodline_compatibility_features(
        self, df: pd.DataFrame, pedigree_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """血統相性・距離適性特徴量（5個）

        Args:
            df: レースデータ
            pedigree_df: 血統データ

        Returns:
            特徴量を追加したデータフレーム
        """
        logger.info("血統相性・距離適性特徴量の抽出開始")
        df_features = df.copy()

        if pedigree_df is not None and "horse_id" in df.columns:
            for horse_id in df["horse_id"].unique():
                horse_pedigree = pedigree_df[pedigree_df["horse_id"] == horse_id]

                if len(horse_pedigree) > 0:
                    # 1. 父×母父の相性スコア（ニックス）
                    if (
                        "sire_name" in horse_pedigree.columns
                        and "dam_sire_name" in horse_pedigree.columns
                    ):
                        sire = horse_pedigree.iloc[0]["sire_name"]
                        dam_sire = horse_pedigree.iloc[0]["dam_sire_name"]

                        # 良好な組み合わせの例（実際はもっと詳細なデータが必要）
                        good_nicks = [
                            ("Deep Impact", "Storm Cat"),
                            ("Deep Impact", "Mr. Prospector"),
                            ("King Kamehameha", "Sunday Silence"),
                            ("Lord Kanaloa", "Sunday Silence"),
                        ]

                        nick_score = 0.5  # デフォルト
                        if (sire, dam_sire) in good_nicks:
                            nick_score = 1.0
                        elif sire == dam_sire:  # 同一は避ける
                            nick_score = 0.2

                        df_features.loc[
                            df_features["horse_id"] == horse_id, "nick_score"
                        ] = nick_score

                    # 2. 距離適性スコア（父系の距離適性とレース距離の一致度）
                    if (
                        "sire_name" in horse_pedigree.columns
                        and "distance" in df.columns
                    ):
                        sire = horse_pedigree.iloc[0]["sire_name"]
                        distance = df[df["horse_id"] == horse_id]["distance"].iloc[0]

                        # 距離カテゴリを判定
                        if distance <= 1400:
                            dist_cat = "sprint"
                        elif distance <= 1800:
                            dist_cat = "mile"
                        elif distance <= 2200:
                            dist_cat = "intermediate"
                        else:
                            dist_cat = "long"

                        # 適性スコア計算
                        aptitude_score = 0.5
                        for cat, sires in self.distance_aptitude.items():
                            if cat == dist_cat and sire in sires:
                                aptitude_score = 1.0
                                break

                        df_features.loc[
                            df_features["horse_id"] == horse_id,
                            "distance_aptitude_score",
                        ] = aptitude_score

                    # 3. インブリード指標（簡易版）
                    if "has_inbreeding" in horse_pedigree.columns:
                        # インブリードがある場合の影響（3×4、4×4など）
                        has_inbreeding = horse_pedigree.iloc[0]["has_inbreeding"]
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "inbreeding_flag"
                        ] = float(has_inbreeding)

                    # 4. 父系と母父系の系統一致度
                    if (
                        "sire_bloodline" in df_features.columns
                        and "dam_sire_bloodline" in df_features.columns
                    ):
                        sire_bl = df_features[df_features["horse_id"] == horse_id][
                            "sire_bloodline"
                        ].iloc[0]
                        dam_sire_bl = df_features[df_features["horse_id"] == horse_id][
                            "dam_sire_bloodline"
                        ].iloc[0]

                        # 同系統の場合
                        if sire_bl == dam_sire_bl and sire_bl != 0:
                            bloodline_match = 1.0
                        # 相性の良い組み合わせ
                        elif (sire_bl, dam_sire_bl) in [
                            (1, 3),
                            (2, 1),
                            (3, 4),
                        ]:  # Sunday×Northern等
                            bloodline_match = 0.8
                        else:
                            bloodline_match = 0.5

                        df_features.loc[
                            df_features["horse_id"] == horse_id, "bloodline_match_score"
                        ] = bloodline_match

                    # 5. 輸入種牡馬フラグ
                    if "is_imported_sire" in horse_pedigree.columns:
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "is_imported_bloodline"
                        ] = float(horse_pedigree.iloc[0]["is_imported_sire"])

        # デフォルト値の設定
        compatibility_features = [
            "nick_score",
            "distance_aptitude_score",
            "inbreeding_flag",
            "bloodline_match_score",
            "is_imported_bloodline",
        ]

        for feat in compatibility_features:
            if feat not in df_features.columns:
                df_features[feat] = 0.5  # 相性系は中央値をデフォルトに
            else:
                df_features[feat] = df_features[feat].fillna(0.5)

        self.feature_names.extend(compatibility_features)
        self.feature_count += 5
        logger.info("血統相性・距離適性特徴量5個を追加")

        return df_features

    def extract_all_pedigree_features(
        self, df: pd.DataFrame, pedigree_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """全血統基本特徴量を抽出（15個）

        Args:
            df: レースデータ
            pedigree_df: 血統データ

        Returns:
            全特徴量を追加したデータフレーム
        """
        logger.info("========== 血統基本特徴量抽出開始 ==========")

        try:
            # 父系特徴量（5個）
            df_features = self.extract_sire_features(df, pedigree_df)

            # 母父系特徴量（5個）
            df_features = self.extract_dam_sire_features(df_features, pedigree_df)

            # 血統相性・距離適性特徴量（5個）
            df_features = self.extract_bloodline_compatibility_features(
                df_features, pedigree_df
            )

            logger.info(
                f"✅ 血統基本特徴量抽出完了: 合計{self.feature_count}個の特徴量を生成"
            )
            logger.info(f"生成された特徴量: {self.feature_names}")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"血統基本特徴量抽出中にエラーが発生しました: {e!s}"
            ) from e

    def get_feature_info(self) -> dict[str, Any]:
        """特徴量情報の取得

        Returns:
            特徴量の情報辞書
        """
        return {
            "feature_names": self.feature_names,
            "feature_count": self.feature_count,
            "categories": {
                "sire": 5,
                "dam_sire": 5,
                "compatibility": 5,
            },
        }
