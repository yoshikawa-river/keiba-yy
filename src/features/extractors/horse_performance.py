from typing import Any, Optional

import numpy as np
import pandas as pd
from loguru import logger

"""馬の成績特徴量抽出モジュール

過去成績から統計的特徴量を生成する。
過去N走の着順、勝率、連対率、複勝率、成績トレンドなど30個の特徴量を抽出。
"""

# from src.core.exceptions import FeatureExtractionError


class FeatureExtractionError(Exception):
    """特徴量抽出エラー"""

    pass


class HorsePerformanceExtractor:
    """馬の成績特徴量を抽出するクラス

    Phase1の基本成績特徴量30個を実装。
    過去の着順統計、生涯成績、条件別成績などを計算。
    """

    def __init__(self):
        """初期化"""
        self.feature_names = []
        self.feature_count = 0

    def extract_past_performance_stats(
        self, df: pd.DataFrame, history_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """過去N走成績統計（15個）

        Args:
            df: レースデータ
            history_df: 過去成績データ

        Returns:
            特徴量を追加したデータフレーム
        """
        logger.info("過去成績統計特徴量の抽出開始")
        df_features = df.copy()

        if history_df is not None and "finish_position" in history_df.columns:
            # 各馬の過去成績を集計
            for horse_id in df["horse_id"].unique():
                horse_history = history_df[
                    history_df["horse_id"] == horse_id
                ].sort_values("race_date", ascending=False)

                # 過去3,5,10走の着順統計
                for n_races in [3, 5, 10]:
                    recent_races = horse_history.head(n_races)["finish_position"]

                    if len(recent_races) > 0:
                        # 平均着順
                        df_features.loc[
                            df_features["horse_id"] == horse_id,
                            f"avg_finish_position_last{n_races}",
                        ] = recent_races.mean()

                        # 中央値
                        df_features.loc[
                            df_features["horse_id"] == horse_id,
                            f"median_finish_position_last{n_races}",
                        ] = recent_races.median()

                        # 標準偏差
                        df_features.loc[
                            df_features["horse_id"] == horse_id,
                            f"std_finish_position_last{n_races}",
                        ] = recent_races.std()

                        # 最高・最低着順
                        if n_races == 5:
                            df_features.loc[
                                df_features["horse_id"] == horse_id, "best_finish_last5"
                            ] = recent_races.min()

                            df_features.loc[
                                df_features["horse_id"] == horse_id,
                                "worst_finish_last5",
                            ] = recent_races.max()

                # 過去10走の勝利数、連対数、複勝数
                recent_10 = horse_history.head(10)["finish_position"]
                if len(recent_10) > 0:
                    df_features.loc[
                        df_features["horse_id"] == horse_id, "win_count_last10"
                    ] = (recent_10 == 1).sum()

                    df_features.loc[
                        df_features["horse_id"] == horse_id, "place_count_last10"
                    ] = (recent_10 <= 2).sum()

                    df_features.loc[
                        df_features["horse_id"] == horse_id, "show_count_last10"
                    ] = (recent_10 <= 3).sum()

                # 着順改善率
                if len(horse_history) >= 2:
                    recent_positions = horse_history.head(5)["finish_position"].values
                    if len(recent_positions) >= 2:
                        improvements = np.diff(recent_positions) * -1  # 改善はマイナス
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "improvement_rate"
                        ] = improvements.mean()

                # 安定性スコア（変動係数の逆数）
                if len(recent_races) >= 3:
                    cv = (
                        recent_races.std() / recent_races.mean()
                        if recent_races.mean() > 0
                        else 1
                    )
                    df_features.loc[
                        df_features["horse_id"] == horse_id, "consistency_score"
                    ] = 1 / (1 + cv)

                # 直近調子トレンド（線形回帰の傾き）
                if len(recent_races) >= 3:
                    x = np.arange(len(recent_races))
                    y = recent_races.values
                    if len(x) == len(y):
                        trend = np.polyfit(x, y, 1)[0]
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "recent_form_trend"
                        ] = trend * -1  # 改善は正の値

        # デフォルト値の設定
        stat_features = [
            "avg_finish_position_last3",
            "avg_finish_position_last5",
            "avg_finish_position_last10",
            "median_finish_position_last3",
            "median_finish_position_last5",
            "std_finish_position_last3",
            "std_finish_position_last5",
            "best_finish_last5",
            "worst_finish_last5",
            "win_count_last10",
            "place_count_last10",
            "show_count_last10",
            "improvement_rate",
            "consistency_score",
            "recent_form_trend",
        ]

        for feat in stat_features:
            if feat not in df_features.columns:
                df_features[feat] = 0
            else:
                df_features[feat] = df_features[feat].fillna(0)

        self.feature_names.extend(stat_features)
        self.feature_count += 15
        logger.info("過去成績統計特徴量15個を追加")

        return df_features

    def extract_career_performance(
        self, df: pd.DataFrame, career_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """生涯成績特徴量（8個）

        Args:
            df: レースデータ
            career_df: 生涯成績データ

        Returns:
            特徴量を追加したデータフレーム
        """
        logger.info("生涯成績特徴量の抽出開始")
        df_features = df.copy()

        if career_df is not None:
            for horse_id in df["horse_id"].unique():
                horse_career = career_df[career_df["horse_id"] == horse_id]

                if len(horse_career) > 0:
                    total_starts = len(horse_career)
                    wins = (horse_career["finish_position"] == 1).sum()
                    places = (horse_career["finish_position"] <= 2).sum()
                    shows = (horse_career["finish_position"] <= 3).sum()

                    # 生涯勝率、連対率、複勝率
                    df_features.loc[
                        df_features["horse_id"] == horse_id, "career_win_rate"
                    ] = wins / total_starts if total_starts > 0 else 0

                    df_features.loc[
                        df_features["horse_id"] == horse_id, "career_place_rate"
                    ] = places / total_starts if total_starts > 0 else 0

                    df_features.loc[
                        df_features["horse_id"] == horse_id, "career_show_rate"
                    ] = shows / total_starts if total_starts > 0 else 0

                    # 生涯出走数
                    df_features.loc[
                        df_features["horse_id"] == horse_id, "career_starts"
                    ] = total_starts

                    # 生涯獲得賞金
                    if "prize_money" in horse_career.columns:
                        total_earnings = horse_career["prize_money"].sum()
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "career_earnings"
                        ] = total_earnings

                        df_features.loc[
                            df_features["horse_id"] == horse_id,
                            "career_earnings_per_start",
                        ] = total_earnings / total_starts if total_starts > 0 else 0

                    # G1・重賞勝利数
                    if "race_grade" in horse_career.columns:
                        g1_wins = (
                            (horse_career["race_grade"] == "G1")
                            & (horse_career["finish_position"] == 1)
                        ).sum()

                        graded_wins = (
                            horse_career["race_grade"].isin(["G1", "G2", "G3"])
                            & (horse_career["finish_position"] == 1)
                        ).sum()

                        df_features.loc[
                            df_features["horse_id"] == horse_id, "career_g1_wins"
                        ] = g1_wins

                        df_features.loc[
                            df_features["horse_id"] == horse_id, "career_graded_wins"
                        ] = graded_wins

        # デフォルト値の設定
        career_features = [
            "career_win_rate",
            "career_place_rate",
            "career_show_rate",
            "career_starts",
            "career_earnings",
            "career_earnings_per_start",
            "career_g1_wins",
            "career_graded_wins",
        ]

        for feat in career_features:
            if feat not in df_features.columns:
                df_features[feat] = 0
            else:
                df_features[feat] = df_features[feat].fillna(0)

        self.feature_names.extend(career_features)
        self.feature_count += 8
        logger.info("生涯成績特徴量8個を追加")

        return df_features

    def extract_conditional_performance(
        self, df: pd.DataFrame, history_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """条件別成績特徴量（7個）

        Args:
            df: レースデータ
            history_df: 過去成績データ（条件情報含む）

        Returns:
            特徴量を追加したデータフレーム
        """
        logger.info("条件別成績特徴量の抽出開始")
        df_features = df.copy()

        if history_df is not None:
            for horse_id in df["horse_id"].unique():
                horse_history = history_df[history_df["horse_id"] == horse_id]

                if len(horse_history) > 0:
                    # 距離カテゴリ別勝率
                    if "distance" in horse_history.columns:
                        distance_categories = pd.cut(
                            horse_history["distance"],
                            bins=[0, 1400, 1800, 2200, 4000],
                            labels=["sprint", "mile", "intermediate", "long"],
                        )

                        current_distance = df[df["horse_id"] == horse_id][
                            "distance"
                        ].iloc[0]
                        current_category = pd.cut(
                            [current_distance],
                            bins=[0, 1400, 1800, 2200, 4000],
                            labels=["sprint", "mile", "intermediate", "long"],
                        )[0]

                        same_category = horse_history[
                            distance_categories == current_category
                        ]
                        if len(same_category) > 0:
                            win_rate = (same_category["finish_position"] == 1).mean()
                            df_features.loc[
                                df_features["horse_id"] == horse_id,
                                "distance_category_win_rate",
                            ] = win_rate

                    # 馬場状態別勝率
                    if (
                        "track_condition" in horse_history.columns
                        and "track_condition" in df.columns
                    ):
                        current_condition = df[df["horse_id"] == horse_id][
                            "track_condition"
                        ].iloc[0]
                        same_condition = horse_history[
                            horse_history["track_condition"] == current_condition
                        ]
                        if len(same_condition) > 0:
                            win_rate = (same_condition["finish_position"] == 1).mean()
                            df_features.loc[
                                df_features["horse_id"] == horse_id,
                                "track_condition_win_rate",
                            ] = win_rate

                    # 競馬場別勝率
                    if "venue" in horse_history.columns and "venue" in df.columns:
                        current_venue = df[df["horse_id"] == horse_id]["venue"].iloc[0]
                        same_venue = horse_history[
                            horse_history["venue"] == current_venue
                        ]
                        if len(same_venue) > 0:
                            win_rate = (same_venue["finish_position"] == 1).mean()
                            df_features.loc[
                                df_features["horse_id"] == horse_id, "venue_win_rate"
                            ] = win_rate

                    # クラス別勝率
                    if (
                        "race_class" in horse_history.columns
                        and "race_class" in df.columns
                    ):
                        current_class = df[df["horse_id"] == horse_id][
                            "race_class"
                        ].iloc[0]
                        same_class = horse_history[
                            horse_history["race_class"] == current_class
                        ]
                        if len(same_class) > 0:
                            win_rate = (same_class["finish_position"] == 1).mean()
                            df_features.loc[
                                df_features["horse_id"] == horse_id, "class_win_rate"
                            ] = win_rate

                    # 季節別勝率
                    if "race_date" in horse_history.columns:
                        horse_history["season"] = pd.to_datetime(
                            horse_history["race_date"]
                        ).dt.month.apply(lambda x: (x % 12 + 3) // 3)

                        if "race_date" in df.columns:
                            current_season = pd.to_datetime(
                                df[df["horse_id"] == horse_id]["race_date"].iloc[0]
                            ).month
                            current_season = (current_season % 12 + 3) // 3

                            same_season = horse_history[
                                horse_history["season"] == current_season
                            ]
                            if len(same_season) > 0:
                                win_rate = (same_season["finish_position"] == 1).mean()
                                df_features.loc[
                                    df_features["horse_id"] == horse_id,
                                    "season_win_rate",
                                ] = win_rate

                    # 枠順別勝率
                    if "post_position" in horse_history.columns:
                        post_categories = pd.cut(
                            horse_history["post_position"],
                            bins=[0, 4, 12, 20],
                            labels=["inner", "middle", "outer"],
                        )

                        if "post_position" in df.columns:
                            current_post = df[df["horse_id"] == horse_id][
                                "post_position"
                            ].iloc[0]
                            current_post_cat = pd.cut(
                                [current_post],
                                bins=[0, 4, 12, 20],
                                labels=["inner", "middle", "outer"],
                            )[0]

                            same_post = horse_history[
                                post_categories == current_post_cat
                            ]
                            if len(same_post) > 0:
                                win_rate = (same_post["finish_position"] == 1).mean()
                                df_features.loc[
                                    df_features["horse_id"] == horse_id,
                                    "position_win_rate",
                                ] = win_rate

                    # 斤量別勝率
                    if "weight_carried" in horse_history.columns:
                        weight_categories = pd.cut(
                            horse_history["weight_carried"],
                            bins=[0, 54, 56, 58, 100],
                            labels=["light", "standard", "heavy", "very_heavy"],
                        )

                        if "weight_carried" in df.columns:
                            current_weight = df[df["horse_id"] == horse_id][
                                "weight_carried"
                            ].iloc[0]
                            current_weight_cat = pd.cut(
                                [current_weight],
                                bins=[0, 54, 56, 58, 100],
                                labels=["light", "standard", "heavy", "very_heavy"],
                            )[0]

                            same_weight = horse_history[
                                weight_categories == current_weight_cat
                            ]
                            if len(same_weight) > 0:
                                win_rate = (same_weight["finish_position"] == 1).mean()
                                df_features.loc[
                                    df_features["horse_id"] == horse_id,
                                    "weight_carried_win_rate",
                                ] = win_rate

        # デフォルト値の設定
        conditional_features = [
            "distance_category_win_rate",
            "track_condition_win_rate",
            "venue_win_rate",
            "class_win_rate",
            "season_win_rate",
            "position_win_rate",
            "weight_carried_win_rate",
        ]

        for feat in conditional_features:
            if feat not in df_features.columns:
                df_features[feat] = 0
            else:
                df_features[feat] = df_features[feat].fillna(0)

        self.feature_names.extend(conditional_features)
        self.feature_count += 7
        logger.info("条件別成績特徴量7個を追加")

        return df_features

    def extract_all_performance_features(
        self,
        df: pd.DataFrame,
        history_df: Optional[pd.DataFrame] = None,
        career_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """全成績特徴量を抽出（30個）

        Args:
            df: レースデータ
            history_df: 過去成績データ
            career_df: 生涯成績データ

        Returns:
            全特徴量を追加したデータフレーム
        """
        logger.info("========== 馬の成績特徴量抽出開始 ==========")

        try:
            # 過去N走成績統計（15個）
            df_features = self.extract_past_performance_stats(df, history_df)

            # 生涯成績（8個）
            df_features = self.extract_career_performance(df_features, career_df)

            # 条件別成績（7個）
            df_features = self.extract_conditional_performance(df_features, history_df)

            logger.info(
                f"✅ 馬の成績特徴量抽出完了: 合計{self.feature_count}個の特徴量を生成"
            )
            logger.info(f"生成された特徴量: {self.feature_names}")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"馬の成績特徴量抽出中にエラーが発生しました: {e!s}"
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
                "past_performance": 15,
                "career_performance": 8,
                "conditional_performance": 7,
            },
        }
