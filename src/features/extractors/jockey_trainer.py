"""騎手・調教師特徴量抽出モジュール

騎手と調教師の成績、相性、コンビネーションなどの特徴量を生成する。
基本的な騎手・調教師特徴量20個を実装。
"""

from typing import Any, Dict

import numpy as np
import pandas as pd
from loguru import logger

# from src.core.exceptions import FeatureExtractionError


class FeatureExtractionError(Exception):
    """特徴量抽出エラー"""

    pass


class JockeyTrainerFeatureExtractor:
    """騎手・調教師特徴量を抽出するクラス

    Phase1の騎手・調教師特徴量20個を実装。
    騎手成績、調教師成績、コンビネーション成績などを計算。
    """

    def __init__(self):
        """初期化"""
        self.feature_names = []
        self.feature_count = 0

    def extract_jockey_features(
        self, df: pd.DataFrame, jockey_stats: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """騎手特徴量（10個）

        Args:
            df: レースデータ
            jockey_stats: 騎手統計データ

        Returns:
            特徴量を追加したデータフレーム
        """
        logger.info("騎手特徴量の抽出開始")
        df_features = df.copy()

        if jockey_stats is not None and "jockey_id" in df.columns:
            for jockey_id in df["jockey_id"].unique():
                if pd.isna(jockey_id):
                    continue

                jockey_data = jockey_stats[jockey_stats["jockey_id"] == jockey_id]

                if len(jockey_data) > 0:
                    # 騎手基本成績
                    total_rides = len(jockey_data)
                    wins = (jockey_data["finish_position"] == 1).sum()
                    places = (jockey_data["finish_position"] <= 2).sum()
                    shows = (jockey_data["finish_position"] <= 3).sum()

                    # 騎手勝率・連対率・複勝率
                    df_features.loc[
                        df_features["jockey_id"] == jockey_id, "jockey_win_rate"
                    ] = wins / total_rides if total_rides > 0 else 0

                    df_features.loc[
                        df_features["jockey_id"] == jockey_id, "jockey_place_rate"
                    ] = places / total_rides if total_rides > 0 else 0

                    df_features.loc[
                        df_features["jockey_id"] == jockey_id, "jockey_show_rate"
                    ] = shows / total_rides if total_rides > 0 else 0

                    # 騎手競馬場別勝率
                    if "venue" in df.columns and "venue" in jockey_data.columns:
                        current_venue = df[df["jockey_id"] == jockey_id]["venue"].iloc[
                            0
                        ]
                        venue_data = jockey_data[jockey_data["venue"] == current_venue]
                        if len(venue_data) > 0:
                            venue_wins = (venue_data["finish_position"] == 1).sum()
                            df_features.loc[
                                df_features["jockey_id"] == jockey_id,
                                "jockey_venue_win_rate",
                            ] = venue_wins / len(venue_data)

                    # 騎手距離別勝率
                    if "distance" in df.columns and "distance" in jockey_data.columns:
                        current_distance = df[df["jockey_id"] == jockey_id][
                            "distance"
                        ].iloc[0]
                        # 距離カテゴリ分け
                        distance_category = self._get_distance_category(
                            current_distance
                        )

                        distance_data = jockey_data[
                            jockey_data["distance"].apply(self._get_distance_category)
                            == distance_category
                        ]
                        if len(distance_data) > 0:
                            distance_wins = (
                                distance_data["finish_position"] == 1
                            ).sum()
                            df_features.loc[
                                df_features["jockey_id"] == jockey_id,
                                "jockey_distance_win_rate",
                            ] = distance_wins / len(distance_data)

                    # 騎手クラス別勝率
                    if (
                        "race_class" in df.columns
                        and "race_class" in jockey_data.columns
                    ):
                        current_class = df[df["jockey_id"] == jockey_id][
                            "race_class"
                        ].iloc[0]
                        class_data = jockey_data[
                            jockey_data["race_class"] == current_class
                        ]
                        if len(class_data) > 0:
                            class_wins = (class_data["finish_position"] == 1).sum()
                            df_features.loc[
                                df_features["jockey_id"] == jockey_id,
                                "jockey_class_win_rate",
                            ] = class_wins / len(class_data)

                    # 騎手と馬の相性（過去の騎乗成績）
                    if "horse_id" in df.columns and "horse_id" in jockey_data.columns:
                        for horse_id in df[df["jockey_id"] == jockey_id][
                            "horse_id"
                        ].unique():
                            horse_combo = jockey_data[
                                jockey_data["horse_id"] == horse_id
                            ]
                            if len(horse_combo) > 0:
                                combo_score = self._calculate_compatibility_score(
                                    horse_combo["finish_position"]
                                )
                                df_features.loc[
                                    (df_features["jockey_id"] == jockey_id)
                                    & (df_features["horse_id"] == horse_id),
                                    "jockey_horse_compatibility",
                                ] = combo_score

                    # 騎手直近調子（最近30日の成績）
                    if "race_date" in jockey_data.columns:
                        recent_data = self._get_recent_data(jockey_data, days=30)
                        if len(recent_data) > 0:
                            recent_wins = (recent_data["finish_position"] == 1).sum()
                            df_features.loc[
                                df_features["jockey_id"] == jockey_id,
                                "jockey_recent_form",
                            ] = recent_wins / len(recent_data)

                    # 騎手賞金ランク（年間獲得賞金順位）
                    if "prize_money" in jockey_data.columns:
                        total_earnings = jockey_data["prize_money"].sum()
                        # 簡易的なランク付け（実際は全騎手でのランキングが必要）
                        earnings_rank = self._get_earnings_rank(total_earnings)
                        df_features.loc[
                            df_features["jockey_id"] == jockey_id,
                            "jockey_earnings_rank",
                        ] = earnings_rank

                    # 騎手経験年数（初騎乗からの年数）
                    if "race_date" in jockey_data.columns:
                        first_ride = pd.to_datetime(jockey_data["race_date"]).min()
                        latest_ride = pd.to_datetime(jockey_data["race_date"]).max()
                        experience_years = (latest_ride - first_ride).days / 365.25
                        df_features.loc[
                            df_features["jockey_id"] == jockey_id,
                            "jockey_experience_years",
                        ] = experience_years

        # デフォルト値の設定
        jockey_features = [
            "jockey_win_rate",
            "jockey_place_rate",
            "jockey_show_rate",
            "jockey_venue_win_rate",
            "jockey_distance_win_rate",
            "jockey_class_win_rate",
            "jockey_horse_compatibility",
            "jockey_recent_form",
            "jockey_earnings_rank",
            "jockey_experience_years",
        ]

        for feat in jockey_features:
            if feat not in df_features.columns:
                df_features[feat] = 0
            else:
                df_features[feat] = df_features[feat].fillna(0)

        self.feature_names.extend(jockey_features)
        self.feature_count += 10
        logger.info("騎手特徴量10個を追加")

        return df_features

    def extract_trainer_features(
        self, df: pd.DataFrame, trainer_stats: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """調教師特徴量（10個）

        Args:
            df: レースデータ
            trainer_stats: 調教師統計データ

        Returns:
            特徴量を追加したデータフレーム
        """
        logger.info("調教師特徴量の抽出開始")
        df_features = df.copy()

        if trainer_stats is not None and "trainer_id" in df.columns:
            for trainer_id in df["trainer_id"].unique():
                if pd.isna(trainer_id):
                    continue

                trainer_data = trainer_stats[trainer_stats["trainer_id"] == trainer_id]

                if len(trainer_data) > 0:
                    # 調教師基本成績
                    total_horses = len(trainer_data)
                    wins = (trainer_data["finish_position"] == 1).sum()
                    places = (trainer_data["finish_position"] <= 2).sum()
                    shows = (trainer_data["finish_position"] <= 3).sum()

                    # 調教師勝率・連対率・複勝率
                    df_features.loc[
                        df_features["trainer_id"] == trainer_id, "trainer_win_rate"
                    ] = wins / total_horses if total_horses > 0 else 0

                    df_features.loc[
                        df_features["trainer_id"] == trainer_id, "trainer_place_rate"
                    ] = places / total_horses if total_horses > 0 else 0

                    df_features.loc[
                        df_features["trainer_id"] == trainer_id, "trainer_show_rate"
                    ] = shows / total_horses if total_horses > 0 else 0

                    # 調教師競馬場別勝率
                    if "venue" in df.columns and "venue" in trainer_data.columns:
                        current_venue = df[df["trainer_id"] == trainer_id][
                            "venue"
                        ].iloc[0]
                        venue_data = trainer_data[
                            trainer_data["venue"] == current_venue
                        ]
                        if len(venue_data) > 0:
                            venue_wins = (venue_data["finish_position"] == 1).sum()
                            df_features.loc[
                                df_features["trainer_id"] == trainer_id,
                                "trainer_venue_win_rate",
                            ] = venue_wins / len(venue_data)

                    # 調教師距離別勝率
                    if "distance" in df.columns and "distance" in trainer_data.columns:
                        current_distance = df[df["trainer_id"] == trainer_id][
                            "distance"
                        ].iloc[0]
                        distance_category = self._get_distance_category(
                            current_distance
                        )

                        distance_data = trainer_data[
                            trainer_data["distance"].apply(self._get_distance_category)
                            == distance_category
                        ]
                        if len(distance_data) > 0:
                            distance_wins = (
                                distance_data["finish_position"] == 1
                            ).sum()
                            df_features.loc[
                                df_features["trainer_id"] == trainer_id,
                                "trainer_distance_win_rate",
                            ] = distance_wins / len(distance_data)

                    # 調教師クラス別勝率
                    if (
                        "race_class" in df.columns
                        and "race_class" in trainer_data.columns
                    ):
                        current_class = df[df["trainer_id"] == trainer_id][
                            "race_class"
                        ].iloc[0]
                        class_data = trainer_data[
                            trainer_data["race_class"] == current_class
                        ]
                        if len(class_data) > 0:
                            class_wins = (class_data["finish_position"] == 1).sum()
                            df_features.loc[
                                df_features["trainer_id"] == trainer_id,
                                "trainer_class_win_rate",
                            ] = class_wins / len(class_data)

                    # 調教師・騎手コンビ成績
                    if (
                        "jockey_id" in df.columns
                        and "jockey_id" in trainer_data.columns
                    ):
                        for jockey_id in df[df["trainer_id"] == trainer_id][
                            "jockey_id"
                        ].unique():
                            if pd.isna(jockey_id):
                                continue
                            combo_data = trainer_data[
                                trainer_data["jockey_id"] == jockey_id
                            ]
                            if len(combo_data) > 0:
                                combo_wins = (combo_data["finish_position"] == 1).sum()
                                df_features.loc[
                                    (df_features["trainer_id"] == trainer_id)
                                    & (df_features["jockey_id"] == jockey_id),
                                    "trainer_jockey_combo",
                                ] = combo_wins / len(combo_data)

                    # 調教師直近調子（最近30日の成績）
                    if "race_date" in trainer_data.columns:
                        recent_data = self._get_recent_data(trainer_data, days=30)
                        if len(recent_data) > 0:
                            recent_wins = (recent_data["finish_position"] == 1).sum()
                            df_features.loc[
                                df_features["trainer_id"] == trainer_id,
                                "trainer_recent_form",
                            ] = recent_wins / len(recent_data)

                    # 厩舎規模（管理馬数）
                    if "horse_id" in trainer_data.columns:
                        unique_horses = trainer_data["horse_id"].nunique()
                        df_features.loc[
                            df_features["trainer_id"] == trainer_id,
                            "trainer_stable_size",
                        ] = unique_horses

                    # 調教師G1勝利数
                    if "race_grade" in trainer_data.columns:
                        g1_wins = (
                            (trainer_data["race_grade"] == "G1")
                            & (trainer_data["finish_position"] == 1)
                        ).sum()
                        df_features.loc[
                            df_features["trainer_id"] == trainer_id, "trainer_g1_wins"
                        ] = g1_wins

        # デフォルト値の設定
        trainer_features = [
            "trainer_win_rate",
            "trainer_place_rate",
            "trainer_show_rate",
            "trainer_venue_win_rate",
            "trainer_distance_win_rate",
            "trainer_class_win_rate",
            "trainer_jockey_combo",
            "trainer_recent_form",
            "trainer_stable_size",
            "trainer_g1_wins",
        ]

        for feat in trainer_features:
            if feat not in df_features.columns:
                df_features[feat] = 0
            else:
                df_features[feat] = df_features[feat].fillna(0)

        self.feature_names.extend(trainer_features)
        self.feature_count += 10
        logger.info("調教師特徴量10個を追加")

        return df_features

    def extract_all_jockey_trainer_features(
        self,
        df: pd.DataFrame,
        jockey_stats: Optional[pd.DataFrame] = None,
        trainer_stats: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """全騎手・調教師特徴量を抽出（20個）

        Args:
            df: レースデータ
            jockey_stats: 騎手統計データ
            trainer_stats: 調教師統計データ

        Returns:
            全特徴量を追加したデータフレーム
        """
        logger.info("========== 騎手・調教師特徴量抽出開始 ==========")

        try:
            # 騎手特徴量（10個）
            df_features = self.extract_jockey_features(df, jockey_stats)

            # 調教師特徴量（10個）
            df_features = self.extract_trainer_features(df_features, trainer_stats)

            logger.info(
                f"✅ 騎手・調教師特徴量抽出完了: 合計{self.feature_count}個の特徴量を生成"
            )
            logger.info(f"生成された特徴量: {self.feature_names}")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"騎手・調教師特徴量抽出中にエラーが発生しました: {e!s}"
            ) from e

    def _get_distance_category(self, distance: int) -> str:
        """距離をカテゴリに分類

        Args:
            distance: 距離（メートル）

        Returns:
            距離カテゴリ
        """
        if distance <= 1400:
            return "sprint"
        if distance <= 1800:
            return "mile"
        if distance <= 2200:
            return "intermediate"
        return "long"

    def _calculate_compatibility_score(self, positions: pd.Series) -> float:
        """相性スコアを計算

        Args:
            positions: 着順のシリーズ

        Returns:
            相性スコア（0-1）
        """
        if len(positions) == 0:
            return 0

        # 着順に応じた重み付けスコア
        scores = []
        for pos in positions:
            if pos == 1:
                scores.append(1.0)
            elif pos == 2:
                scores.append(0.8)
            elif pos == 3:
                scores.append(0.6)
            elif pos <= 5:
                scores.append(0.4)
            elif pos <= 10:
                scores.append(0.2)
            else:
                scores.append(0.1)

        return np.mean(scores)

    def _get_recent_data(self, data: pd.DataFrame, days: int = 30) -> pd.DataFrame:
        """最近のデータを取得

        Args:
            data: データフレーム
            days: 取得する日数

        Returns:
            最近のデータ
        """
        if "race_date" not in data.columns:
            return pd.DataFrame()

        data["race_date"] = pd.to_datetime(data["race_date"])
        latest_date = data["race_date"].max()
        cutoff_date = latest_date - pd.Timedelta(days=days)

        return data[data["race_date"] >= cutoff_date]

    def _get_earnings_rank(self, total_earnings: float) -> int:
        """獲得賞金からランクを計算

        Args:
            total_earnings: 総獲得賞金

        Returns:
            ランク（1-10）
        """
        # 簡易的なランク付け（実際は全騎手/調教師での相対順位が必要）
        if total_earnings >= 1000000000:  # 10億円以上
            return 1
        if total_earnings >= 500000000:  # 5億円以上
            return 2
        if total_earnings >= 200000000:  # 2億円以上
            return 3
        if total_earnings >= 100000000:  # 1億円以上
            return 4
        if total_earnings >= 50000000:  # 5000万円以上
            return 5
        if total_earnings >= 20000000:  # 2000万円以上
            return 6
        if total_earnings >= 10000000:  # 1000万円以上
            return 7
        if total_earnings >= 5000000:  # 500万円以上
            return 8
        if total_earnings >= 1000000:  # 100万円以上
            return 9
        return 10

    def get_feature_info(self) -> Dict[str, Any]:
        """特徴量情報の取得

        Returns:
            特徴量の情報辞書
        """
        return {
            "feature_names": self.feature_names,
            "feature_count": self.feature_count,
            "categories": {"jockey": 10, "trainer": 10},
        }
