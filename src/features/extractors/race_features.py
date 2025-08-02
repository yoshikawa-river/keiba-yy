"""レース特徴量抽出機能

レースのレベル、出走頭数、ペース予想、展開予想などを抽出する
"""

import numpy as np
import pandas as pd
from loguru import logger

from src.core.exceptions import FeatureExtractionError


class RaceFeatureExtractor:
    """レース特徴量を抽出するクラス"""

    def __init__(self):
        """初期化"""
        self.feature_names = []
        self.pace_categories = ["slow", "medium", "fast", "very_fast"]

    def extract_race_level_features(
        self, df: pd.DataFrame, historical_races: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """レースレベル特徴量の抽出

        Args:
            df: 現在のレースデータ
            historical_races: 過去のレース結果データ

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("レースレベル特徴量抽出開始")

        try:
            df_features = df.copy()

            # レースクラスのランク付け
            class_rank_map = {
                "G1": 10,
                "GⅠ": 10,
                "G2": 9,
                "GⅡ": 9,
                "G3": 8,
                "GⅢ": 8,
                "L": 7,
                "Listed": 7,
                "オープン": 6,
                "OP": 6,
                "Open": 6,
                "3勝": 5,
                "1600万": 5,
                "2勝": 4,
                "1000万": 4,
                "1勝": 3,
                "500万": 3,
                "新馬": 2,
                "未勝利": 1,
            }

            if "race_class" in df.columns:
                df_features["race_class_rank"] = (
                    df["race_class"].map(class_rank_map).fillna(0)
                )

                # 重賞レースフラグ
                df_features["is_graded_race"] = df_features["race_class_rank"] >= 8
                df_features["is_g1_race"] = df_features["race_class_rank"] == 10

                self.feature_names.extend(
                    ["race_class_rank", "is_graded_race", "is_g1_race"]
                )

            # 賞金総額
            if "total_prize" in df.columns:
                df_features["total_prize_log"] = np.log1p(df["total_prize"])
                # 賞金レベルカテゴリ
                df_features["prize_level"] = pd.qcut(
                    df["total_prize"],
                    q=5,
                    labels=["very_low", "low", "medium", "high", "very_high"],
                    duplicates="drop",
                )
                self.feature_names.extend(["total_prize_log", "prize_level"])

            # 過去の同レースの平均タイム（レースレベル指標）
            if historical_races is not None and "race_name" in df.columns:
                race_time_stats = []

                for idx, row in df.iterrows():
                    race_name = row["race_name"]
                    distance = row.get("distance", None)

                    # 同じレースの過去データ
                    same_race = historical_races[
                        (historical_races["race_name"] == race_name)
                        & (historical_races["distance"] == distance)
                        if distance
                        else True
                    ]

                    if len(same_race) > 0 and "winning_time" in same_race.columns:
                        stats = {
                            "historical_avg_time": same_race["winning_time"].mean(),
                            "historical_best_time": same_race["winning_time"].min(),
                            "historical_time_std": same_race["winning_time"].std(),
                        }
                    else:
                        stats = {
                            "historical_avg_time": np.nan,
                            "historical_best_time": np.nan,
                            "historical_time_std": np.nan,
                        }

                    race_time_stats.append(stats)

                if race_time_stats:
                    time_df = pd.DataFrame(race_time_stats, index=df.index)
                    df_features = pd.concat([df_features, time_df], axis=1)
                    self.feature_names.extend(time_df.columns.tolist())

            # 年齢制限
            if "age_restriction" in df.columns:
                age_dummies = pd.get_dummies(
                    df["age_restriction"], prefix="age_restrict"
                )
                df_features = pd.concat([df_features, age_dummies], axis=1)
                self.feature_names.extend(age_dummies.columns.tolist())

            # 性別制限
            if "sex_restriction" in df.columns:
                df_features["has_sex_restriction"] = (
                    ~df["sex_restriction"].isna()
                ).astype(int)
                df_features["is_fillies_only"] = (df["sex_restriction"] == "牝").astype(
                    int
                )
                self.feature_names.extend(["has_sex_restriction", "is_fillies_only"])

            logger.info("レースレベル特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"レースレベル特徴量抽出中にエラーが発生しました: {e!s}"
            )

    def extract_field_competition_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """出走馬の競争レベル特徴量抽出

        Args:
            df: 現在のレースデータ（同一レースの全馬データ）

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("出走馬競争レベル特徴量抽出開始")

        try:
            df_features = df.copy()

            # レースごとにグループ化して処理
            if "race_id" in df.columns:
                competition_features = []

                for race_id, race_group in df.groupby("race_id"):
                    # 各馬の過去成績統計があることを前提
                    if "career_win_rate" in race_group.columns:
                        # フィールド全体の統計
                        field_stats = {
                            "field_avg_win_rate": race_group["career_win_rate"].mean(),
                            "field_max_win_rate": race_group["career_win_rate"].max(),
                            "field_std_win_rate": race_group["career_win_rate"].std(),
                        }
                    else:
                        field_stats = {
                            "field_avg_win_rate": np.nan,
                            "field_max_win_rate": np.nan,
                            "field_std_win_rate": np.nan,
                        }

                    # 各馬の相対的な強さ
                    for idx in race_group.index:
                        horse_stats = field_stats.copy()

                        if "career_win_rate" in race_group.columns:
                            own_win_rate = race_group.loc[idx, "career_win_rate"]
                            # 自分より強い馬の数
                            horse_stats["stronger_horses_count"] = (
                                race_group["career_win_rate"] > own_win_rate
                            ).sum()
                            # 相対的な強さ（1が最強）
                            horse_stats["relative_strength_rank"] = (
                                race_group["career_win_rate"]
                                .rank(ascending=False)
                                .loc[idx]
                            )
                            # 勝率の偏差値
                            if field_stats["field_std_win_rate"] > 0:
                                horse_stats["win_rate_deviation"] = (
                                    own_win_rate - field_stats["field_avg_win_rate"]
                                ) / field_stats["field_std_win_rate"]
                            else:
                                horse_stats["win_rate_deviation"] = 0

                        competition_features.append(horse_stats)

                if competition_features:
                    comp_df = pd.DataFrame(competition_features, index=df.index)
                    df_features = pd.concat([df_features, comp_df], axis=1)
                    self.feature_names.extend(comp_df.columns.tolist())

            # 人気（オッズ）による競争レベル
            if "odds" in df.columns:
                # オッズの逆数を確率として扱う
                df_features["implied_probability"] = 1 / (df["odds"] + 1)

                if "race_id" in df.columns:
                    # レースごとの統計
                    race_odds_stats = df.groupby("race_id")["odds"].agg(
                        ["mean", "std", "min"]
                    )
                    df_features = df_features.merge(
                        race_odds_stats,
                        left_on="race_id",
                        right_index=True,
                        suffixes=("", "_field"),
                    )

                    # 相対オッズ
                    df_features["relative_odds"] = (
                        df_features["odds"] / df_features["mean"]
                    )
                    df_features["is_favorite"] = (
                        df_features["odds"] == df_features["min"]
                    ).astype(int)

                    self.feature_names.extend(
                        ["implied_probability", "relative_odds", "is_favorite"]
                    )

            logger.info("出走馬競争レベル特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"出走馬競争レベル特徴量抽出中にエラーが発生しました: {e!s}"
            )

    def extract_pace_features(
        self, df: pd.DataFrame, historical_lap_times: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """ペース予想特徴量の抽出

        Args:
            df: 現在のレースデータ
            historical_lap_times: 過去のラップタイムデータ

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("ペース予想特徴量抽出開始")

        try:
            df_features = df.copy()

            # 距離によるペース傾向
            if "distance" in df.columns:
                # 距離別の標準ペース
                distance_pace_map = {
                    1000: "very_fast",
                    1200: "very_fast",
                    1400: "fast",
                    1600: "fast",
                    1800: "medium",
                    2000: "medium",
                    2200: "medium",
                    2400: "slow",
                    2500: "slow",
                    3000: "slow",
                    3200: "slow",
                }

                def get_expected_pace(distance):
                    for d, pace in sorted(distance_pace_map.items()):
                        if distance <= d:
                            return pace
                    return "slow"

                df_features["expected_pace"] = df["distance"].apply(get_expected_pace)
                pace_dummies = pd.get_dummies(
                    df_features["expected_pace"], prefix="pace"
                )
                df_features = pd.concat([df_features, pace_dummies], axis=1)
                self.feature_names.extend(pace_dummies.columns.tolist())

            # 逃げ馬の数による展開予想
            if "running_style" in df.columns and "race_id" in df.columns:
                pace_features = []

                for race_id, race_group in df.groupby("race_id"):
                    # 脚質別の頭数
                    style_counts = race_group["running_style"].value_counts()

                    pace_stats = {
                        "front_runners_count": style_counts.get("逃げ", 0),
                        "stalkers_count": style_counts.get("先行", 0),
                        "midfield_count": style_counts.get("差し", 0),
                        "closers_count": style_counts.get("追込", 0),
                    }

                    # ペース予想
                    if pace_stats["front_runners_count"] >= 3:
                        pace_stats["predicted_pace"] = "very_fast"
                    elif pace_stats["front_runners_count"] >= 2:
                        pace_stats["predicted_pace"] = "fast"
                    elif pace_stats["front_runners_count"] == 0:
                        pace_stats["predicted_pace"] = "slow"
                    else:
                        pace_stats["predicted_pace"] = "medium"

                    # 展開の複雑さ
                    pace_stats["pace_complexity"] = (
                        pace_stats["front_runners_count"] * 2
                        + pace_stats["stalkers_count"]
                    ) / len(race_group)

                    for idx in race_group.index:
                        pace_features.append(pace_stats)

                if pace_features:
                    pace_df = pd.DataFrame(pace_features, index=df.index)
                    df_features = pd.concat([df_features, pace_df], axis=1)
                    self.feature_names.extend(pace_df.columns.tolist())

            # 過去のラップタイムからのペース分析
            if historical_lap_times is not None and "race_id" in df.columns:
                # 実装は省略（実際のデータ構造に依存）
                pass

            logger.info("ペース予想特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"ペース予想特徴量抽出中にエラーが発生しました: {e!s}"
            )

    def extract_position_advantage_features(
        self, df: pd.DataFrame, course_statistics: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """枠順・コース形態による有利不利特徴量

        Args:
            df: 現在のレースデータ
            course_statistics: コース別の枠順成績統計

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("枠順有利不利特徴量抽出開始")

        try:
            df_features = df.copy()

            # コース形態による内外の有利不利
            course_advantages = {
                # 競馬場: (内枠有利度, 外枠有利度) 0-1のスコア
                "東京": (0.3, 0.7),  # 外枠有利
                "中山": (0.7, 0.3),  # 内枠有利
                "阪神": (0.5, 0.5),  # 中立
                "京都": (0.6, 0.4),  # やや内枠有利
                "中京": (0.5, 0.5),  # 中立
                "新潟": (0.4, 0.6),  # やや外枠有利
                "福島": (0.6, 0.4),  # やや内枠有利
                "札幌": (0.5, 0.5),  # 中立
                "函館": (0.6, 0.4),  # やや内枠有利
                "小倉": (0.5, 0.5),  # 中立
            }

            if "racecourse" in df.columns and "post_position" in df.columns:
                position_features = []

                for idx, row in df.iterrows():
                    course = row["racecourse"]
                    position = row["post_position"]
                    field_size = row.get("field_size", 18)

                    features = {}

                    if course in course_advantages:
                        inner_adv, outer_adv = course_advantages[course]

                        # 相対的な枠順位置（0-1）
                        relative_position = (
                            (position - 1) / (field_size - 1) if field_size > 1 else 0.5
                        )

                        # 有利度スコア
                        features["position_advantage_score"] = (
                            inner_adv * (1 - relative_position)
                            + outer_adv * relative_position
                        )

                        # 内枠・外枠の絶対的な判定
                        features["is_inner_draw"] = (
                            1 if position <= field_size * 0.3 else 0
                        )
                        features["is_outer_draw"] = (
                            1 if position >= field_size * 0.7 else 0
                        )
                        features["is_middle_draw"] = (
                            1 - features["is_inner_draw"] - features["is_outer_draw"]
                        )
                    else:
                        features["position_advantage_score"] = 0.5
                        features["is_inner_draw"] = 0
                        features["is_outer_draw"] = 0
                        features["is_middle_draw"] = 1

                    position_features.append(features)

                if position_features:
                    pos_df = pd.DataFrame(position_features, index=df.index)
                    df_features = pd.concat([df_features, pos_df], axis=1)
                    self.feature_names.extend(pos_df.columns.tolist())

            # コース統計からの詳細な有利不利
            if course_statistics is not None:
                # 実装は省略（実際のデータ構造に依存）
                pass

            logger.info("枠順有利不利特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"枠順有利不利特徴量抽出中にエラーが発生しました: {e!s}"
            )

    def extract_seasonal_race_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """季節・時期による特徴量抽出

        Args:
            df: 現在のレースデータ

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("季節・時期特徴量抽出開始")

        try:
            df_features = df.copy()

            if "race_date" in df.columns:
                # 日付型に変換
                df_features["race_date"] = pd.to_datetime(df["race_date"])

                # 月・季節
                df_features["race_month"] = df_features["race_date"].dt.month

                def get_season(month):
                    if month in [3, 4, 5]:
                        return "spring"
                    if month in [6, 7, 8]:
                        return "summer"
                    if month in [9, 10, 11]:
                        return "autumn"
                    return "winter"

                df_features["race_season"] = df_features["race_month"].apply(get_season)

                # 季節ダミー変数
                season_dummies = pd.get_dummies(
                    df_features["race_season"], prefix="season"
                )
                df_features = pd.concat([df_features, season_dummies], axis=1)

                # 重要開催時期
                df_features["is_spring_classics"] = (
                    (df_features["race_month"].isin([3, 4, 5]))
                    & (df_features.get("race_class_rank", 0) >= 8)
                ).astype(int)

                df_features["is_autumn_classics"] = (
                    (df_features["race_month"].isin([10, 11]))
                    & (df_features.get("race_class_rank", 0) >= 8)
                ).astype(int)

                df_features["is_summer_series"] = (
                    df_features["race_month"].isin([7, 8])
                ).astype(int)

                df_features["is_year_end"] = (df_features["race_month"] == 12).astype(
                    int
                )

                self.feature_names.extend(
                    [
                        "race_month",
                        "is_spring_classics",
                        "is_autumn_classics",
                        "is_summer_series",
                        "is_year_end",
                    ]
                )
                self.feature_names.extend(season_dummies.columns.tolist())

            logger.info("季節・時期特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"季節・時期特徴量抽出中にエラーが発生しました: {e!s}"
            )

    def extract_all_race_features(
        self,
        df: pd.DataFrame,
        historical_races: pd.DataFrame | None = None,
        historical_lap_times: pd.DataFrame | None = None,
        course_statistics: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """全てのレース特徴量を抽出

        Args:
            df: 現在のレースデータ
            historical_races: 過去のレース結果データ
            historical_lap_times: 過去のラップタイムデータ
            course_statistics: コース別統計データ

        Returns:
            全特徴量追加後のデータフレーム
        """
        logger.info("全レース特徴量抽出開始")

        try:
            # レースレベル特徴量
            df_features = self.extract_race_level_features(df, historical_races)

            # 出走馬競争レベル特徴量
            df_features = self.extract_field_competition_features(df_features)

            # ペース予想特徴量
            df_features = self.extract_pace_features(df_features, historical_lap_times)

            # 枠順有利不利特徴量
            df_features = self.extract_position_advantage_features(
                df_features, course_statistics
            )

            # 季節・時期特徴量
            df_features = self.extract_seasonal_race_features(df_features)

            logger.info(f"全レース特徴量抽出完了: 特徴量数={len(self.feature_names)}")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"全レース特徴量抽出中にエラーが発生しました: {e!s}"
            )
