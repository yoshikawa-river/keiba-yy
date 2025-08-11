"""過去成績特徴量抽出機能

通算成績、直近N走の成績、コース別成績、距離別成績、馬場状態別成績などを抽出する
"""

from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from src.core.exceptions import FeatureExtractionError


class PerformanceFeatureExtractor:
    """過去成績特徴量を抽出するクラス"""

    def __init__(self):
        """初期化"""
        self.feature_names = []
        self.performance_windows = [3, 5, 10]  # 直近N走の設定
        self.feature_count = 0  # 特徴量カウント管理

    def extract_career_performance(
        self,
        df: pd.DataFrame,
        performance_history: pd.DataFrame,
        entity_column: str = "horse_id",
        date_column: str = "race_date",
    ) -> pd.DataFrame:
        """通算成績特徴量の抽出

        Args:
            df: 現在のレースデータ
            performance_history: 過去の成績データ
            entity_column: エンティティカラム(馬、騎手など)
            date_column: 日付カラム

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info(f"通算成績特徴量抽出開始: entity={entity_column}")

        try:
            df_features = df.copy()

            # 各エンティティの通算成績を計算
            career_stats = []

            for idx, row in df.iterrows():
                entity_id = row[entity_column]
                current_date = row[date_column]

                # 過去の成績を取得(現在のレースより前)
                past_results = performance_history[
                    (performance_history[entity_column] == entity_id)
                    & (performance_history[date_column] < current_date)
                ]

                if len(past_results) == 0:
                    # 初出走の場合
                    stats = {
                        "career_starts": 0,
                        "career_wins": 0,
                        "career_places": 0,
                        "career_shows": 0,
                        "career_win_rate": 0,
                        "career_place_rate": 0,
                        "career_show_rate": 0,
                        "career_earnings": 0,
                        "career_avg_finish": np.nan,
                        "career_best_finish": np.nan,
                        "career_worst_finish": np.nan,
                        "career_finish_std": np.nan,
                    }
                else:
                    # 通算成績を計算
                    starts = len(past_results)
                    wins = (past_results["finish_position"] == 1).sum()
                    places = (past_results["finish_position"] <= 2).sum()
                    shows = (past_results["finish_position"] <= 3).sum()

                    stats = {
                        "career_starts": starts,
                        "career_wins": wins,
                        "career_places": places,
                        "career_shows": shows,
                        "career_win_rate": wins / starts,
                        "career_place_rate": places / starts,
                        "career_show_rate": shows / starts,
                        "career_earnings": past_results["prize_money"].sum()
                        if "prize_money" in past_results
                        else 0,
                        "career_avg_finish": past_results["finish_position"].mean(),
                        "career_best_finish": past_results["finish_position"].min(),
                        "career_worst_finish": past_results["finish_position"].max(),
                        "career_finish_std": past_results["finish_position"].std(),
                    }

                career_stats.append(stats)

            # データフレームに結合
            career_df = pd.DataFrame(career_stats, index=df.index)
            df_features = pd.concat([df_features, career_df], axis=1)

            self.feature_names.extend(career_df.columns.tolist())
            self.feature_count += len(career_df.columns)

            logger.info(f"通算成績特徴量抽出完了: 特徴量数={len(career_df.columns)}")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"通算成績特徴量抽出中にエラーが発生しました: {e!s}"
            ) from e

    def extract_recent_performance(
        self,
        df: pd.DataFrame,
        performance_history: pd.DataFrame,
        entity_column: str = "horse_id",
        date_column: str = "race_date",
        n_recent: Optional[list[int]] = None,
    ) -> pd.DataFrame:
        """直近N走の成績特徴量抽出

        Args:
            df: 現在のレースデータ
            performance_history: 過去の成績データ
            entity_column: エンティティカラム
            date_column: 日付カラム
            n_recent: 直近N走のリスト

        Returns:
            特徴量追加後のデータフレーム
        """
        if n_recent is None:
            n_recent = self.performance_windows

        logger.info(f"直近成績特徴量抽出開始: windows={n_recent}")

        try:
            df_features = df.copy()

            for n in n_recent:
                recent_stats = []

                for idx, row in df.iterrows():
                    entity_id = row[entity_column]
                    current_date = row[date_column]

                    # 直近N走の成績を取得
                    past_results = (
                        performance_history[
                            (performance_history[entity_column] == entity_id)
                            & (performance_history[date_column] < current_date)
                        ]
                        .sort_values(date_column, ascending=False)
                        .head(n)
                    )

                    if len(past_results) == 0:
                        # 過去成績なし
                        stats = {
                            f"recent{n}_starts": 0,
                            f"recent{n}_wins": 0,
                            f"recent{n}_win_rate": 0,
                            f"recent{n}_avg_finish": np.nan,
                            f"recent{n}_best_finish": np.nan,
                            f"recent{n}_finish_trend": 0,
                            f"recent{n}_consistency": np.nan,
                        }
                    else:
                        # 直近成績を計算
                        starts = len(past_results)
                        wins = (past_results["finish_position"] == 1).sum()
                        positions = past_results["finish_position"].values

                        # トレンド計算(改善=正、悪化=負)
                        if len(positions) > 1:
                            trend = (
                                np.polyfit(range(len(positions)), positions, 1)[0] * -1
                            )
                        else:
                            trend = 0

                        stats = {
                            f"recent{n}_starts": starts,
                            f"recent{n}_wins": wins,
                            f"recent{n}_win_rate": wins / starts,
                            f"recent{n}_avg_finish": positions.mean(),
                            f"recent{n}_best_finish": positions.min(),
                            f"recent{n}_finish_trend": trend,
                            f"recent{n}_consistency": positions.std()
                            if len(positions) > 1
                            else np.nan,
                        }

                        # 連勝・連敗の計算
                        if len(positions) > 0:
                            streak = self._calculate_streak(positions)
                            stats[f"recent{n}_streak"] = streak

                    recent_stats.append(stats)

                # データフレームに結合
                recent_df = pd.DataFrame(recent_stats, index=df.index)
                df_features = pd.concat([df_features, recent_df], axis=1)

                self.feature_names.extend(recent_df.columns.tolist())
                self.feature_count += len(recent_df.columns)

            logger.info("直近成績特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"直近成績特徴量抽出中にエラーが発生しました: {e!s}"
            ) from e

    def extract_course_performance(
        self,
        df: pd.DataFrame,
        performance_history: pd.DataFrame,
        entity_column: str = "horse_id",
        date_column: str = "race_date",
    ) -> pd.DataFrame:
        """コース別成績特徴量の抽出

        Args:
            df: 現在のレースデータ
            performance_history: 過去の成績データ
            entity_column: エンティティカラム
            date_column: 日付カラム

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("コース別成績特徴量抽出開始")

        try:
            df_features = df.copy()
            course_stats = []

            for idx, row in df.iterrows():
                entity_id = row[entity_column]
                current_date = row[date_column]
                current_course = row.get("racecourse", None)

                stats = {}

                # 同じ競馬場での成績
                if current_course:
                    same_course = performance_history[
                        (performance_history[entity_column] == entity_id)
                        & (performance_history[date_column] < current_date)
                        & (performance_history["racecourse"] == current_course)
                    ]

                    if len(same_course) > 0:
                        stats["same_course_starts"] = len(same_course)
                        stats["same_course_wins"] = (
                            same_course["finish_position"] == 1
                        ).sum()
                        stats["same_course_win_rate"] = (
                            stats["same_course_wins"] / stats["same_course_starts"]
                        )
                        stats["same_course_avg_finish"] = same_course[
                            "finish_position"
                        ].mean()
                    else:
                        stats["same_course_starts"] = 0
                        stats["same_course_wins"] = 0
                        stats["same_course_win_rate"] = 0
                        stats["same_course_avg_finish"] = np.nan

                # 左回り・右回りでの成績
                if "turn_direction" in row:
                    turn_dir = row["turn_direction"]
                    same_turn = performance_history[
                        (performance_history[entity_column] == entity_id)
                        & (performance_history[date_column] < current_date)
                        & (performance_history["turn_direction"] == turn_dir)
                    ]

                    if len(same_turn) > 0:
                        stats[f"{turn_dir}_turn_starts"] = len(same_turn)
                        stats[f"{turn_dir}_turn_win_rate"] = (
                            same_turn["finish_position"] == 1
                        ).sum() / len(same_turn)
                        stats[f"{turn_dir}_turn_avg_finish"] = same_turn[
                            "finish_position"
                        ].mean()

                course_stats.append(stats)

            # データフレームに結合
            if course_stats and course_stats[0]:  # 空でない場合のみ
                course_df = pd.DataFrame(course_stats, index=df.index)
                df_features = pd.concat([df_features, course_df], axis=1)
                self.feature_names.extend(course_df.columns.tolist())
                self.feature_count += len(course_df.columns)

            logger.info("コース別成績特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"コース別成績特徴量抽出中にエラーが発生しました: {e!s}"
            ) from e

    def extract_distance_performance(
        self,
        df: pd.DataFrame,
        performance_history: pd.DataFrame,
        entity_column: str = "horse_id",
        date_column: str = "race_date",
        distance_ranges: Optional[list[tuple[int, int]]] = None,
    ) -> pd.DataFrame:
        """距離別成績特徴量の抽出

        Args:
            df: 現在のレースデータ
            performance_history: 過去の成績データ
            entity_column: エンティティカラム
            date_column: 日付カラム
            distance_ranges: 距離範囲のリスト

        Returns:
            特徴量追加後のデータフレーム
        """
        if distance_ranges is None:
            distance_ranges = [
                (0, 1400),  # 短距離
                (1401, 1800),  # マイル
                (1801, 2200),  # 中距離
                (2201, 9999),  # 長距離
            ]

        logger.info("距離別成績特徴量抽出開始")

        try:
            df_features = df.copy()
            distance_stats = []

            for idx, row in df.iterrows():
                entity_id = row[entity_column]
                current_date = row[date_column]
                current_distance = row.get("distance", None)

                stats = {}

                if current_distance:
                    # 同じ距離カテゴリでの成績
                    for i, (min_dist, max_dist) in enumerate(distance_ranges):
                        if min_dist <= current_distance <= max_dist:
                            same_category = performance_history[
                                (performance_history[entity_column] == entity_id)
                                & (performance_history[date_column] < current_date)
                                & (performance_history["distance"] >= min_dist)
                                & (performance_history["distance"] <= max_dist)
                            ]

                            category_name = self._get_distance_category_name(i)

                            if len(same_category) > 0:
                                stats[f"{category_name}_starts"] = len(same_category)
                                stats[f"{category_name}_wins"] = (
                                    same_category["finish_position"] == 1
                                ).sum()
                                stats[f"{category_name}_win_rate"] = (
                                    stats[f"{category_name}_wins"]
                                    / stats[f"{category_name}_starts"]
                                )
                                stats[f"{category_name}_avg_finish"] = same_category[
                                    "finish_position"
                                ].mean()
                            else:
                                stats[f"{category_name}_starts"] = 0
                                stats[f"{category_name}_wins"] = 0
                                stats[f"{category_name}_win_rate"] = 0
                                stats[f"{category_name}_avg_finish"] = np.nan

                            break

                    # 完全に同じ距離での成績
                    exact_distance = performance_history[
                        (performance_history[entity_column] == entity_id)
                        & (performance_history[date_column] < current_date)
                        & (performance_history["distance"] == current_distance)
                    ]

                    if len(exact_distance) > 0:
                        stats["exact_distance_starts"] = len(exact_distance)
                        stats["exact_distance_win_rate"] = (
                            exact_distance["finish_position"] == 1
                        ).sum() / len(exact_distance)

                distance_stats.append(stats)

            # データフレームに結合
            if distance_stats and distance_stats[0]:  # 空でない場合のみ
                distance_df = pd.DataFrame(distance_stats, index=df.index)
                df_features = pd.concat([df_features, distance_df], axis=1)
                self.feature_names.extend(distance_df.columns.tolist())
                self.feature_count += len(distance_df.columns)

            logger.info("距離別成績特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"距離別成績特徴量抽出中にエラーが発生しました: {e!s}"
            ) from e

    def extract_track_condition_performance(
        self,
        df: pd.DataFrame,
        performance_history: pd.DataFrame,
        entity_column: str = "horse_id",
        date_column: str = "race_date",
    ) -> pd.DataFrame:
        """馬場状態別成績特徴量の抽出

        Args:
            df: 現在のレースデータ
            performance_history: 過去の成績データ
            entity_column: エンティティカラム
            date_column: 日付カラム

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("馬場状態別成績特徴量抽出開始")

        try:
            df_features = df.copy()
            condition_stats = []

            for idx, row in df.iterrows():
                entity_id = row[entity_column]
                current_date = row[date_column]
                current_track_type = row.get("track_type", None)
                current_condition = row.get("track_condition", None)

                stats = {}

                # 芝・ダート別成績
                if current_track_type:
                    same_track_type = performance_history[
                        (performance_history[entity_column] == entity_id)
                        & (performance_history[date_column] < current_date)
                        & (performance_history["track_type"] == current_track_type)
                    ]

                    if len(same_track_type) > 0:
                        stats[f"{current_track_type}_starts"] = len(same_track_type)
                        stats[f"{current_track_type}_win_rate"] = (
                            same_track_type["finish_position"] == 1
                        ).sum() / len(same_track_type)
                        stats[f"{current_track_type}_avg_finish"] = same_track_type[
                            "finish_position"
                        ].mean()

                # 馬場状態別成績
                if current_condition:
                    # 良馬場
                    good_condition = performance_history[
                        (performance_history[entity_column] == entity_id)
                        & (performance_history[date_column] < current_date)
                        & (
                            performance_history["track_condition"].isin(
                                ["firm", "good"]
                            )
                        )
                    ]

                    if len(good_condition) > 0:
                        stats["good_condition_starts"] = len(good_condition)
                        stats["good_condition_win_rate"] = (
                            good_condition["finish_position"] == 1
                        ).sum() / len(good_condition)

                    # 重・不良馬場
                    bad_condition = performance_history[
                        (performance_history[entity_column] == entity_id)
                        & (performance_history[date_column] < current_date)
                        & (
                            performance_history["track_condition"].isin(
                                ["soft", "heavy", "yielding"]
                            )
                        )
                    ]

                    if len(bad_condition) > 0:
                        stats["bad_condition_starts"] = len(bad_condition)
                        stats["bad_condition_win_rate"] = (
                            bad_condition["finish_position"] == 1
                        ).sum() / len(bad_condition)

                condition_stats.append(stats)

            # データフレームに結合
            if condition_stats and condition_stats[0]:  # 空でない場合のみ
                condition_df = pd.DataFrame(condition_stats, index=df.index)
                df_features = pd.concat([df_features, condition_df], axis=1)
                self.feature_names.extend(condition_df.columns.tolist())
                self.feature_count += len(condition_df.columns)

            logger.info("馬場状態別成績特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"馬場状態別成績特徴量抽出中にエラーが発生しました: {e!s}"
            ) from e

    def _calculate_streak(self, positions: np.ndarray) -> int:
        """連勝・連敗の計算

        Args:
            positions: 着順の配列(新しい順)

        Returns:
            連勝数(正)または連敗数(負)
        """
        if len(positions) == 0:
            return 0

        streak = 0

        # 最新の結果から確認
        if positions[0] == 1:
            # 連勝をカウント
            for pos in positions:
                if pos == 1:
                    streak += 1
                else:
                    break
        elif positions[0] > 3:
            # 連敗をカウント(4着以下)
            for pos in positions:
                if pos > 3:
                    streak -= 1
                else:
                    break

        return streak

    def _get_distance_category_name(self, index: int) -> str:
        """距離カテゴリ名の取得

        Args:
            index: カテゴリインデックス

        Returns:
            カテゴリ名
        """
        return ["sprint", "mile", "intermediate", "long"]

    def extract_all_performance_features(
        self,
        df: pd.DataFrame,
        performance_history: pd.DataFrame,
        entity_column: str = "horse_id",
        date_column: str = "race_date",
    ) -> pd.DataFrame:
        """全ての過去成績特徴量を抽出

        Args:
            df: 現在のレースデータ
            performance_history: 過去の成績データ
            entity_column: エンティティカラム
            date_column: 日付カラム

        Returns:
            全特徴量追加後のデータフレーム
        """
        logger.info("全過去成績特徴量抽出開始")

        try:
            # 通算成績
            df_features = self.extract_career_performance(
                df, performance_history, entity_column, date_column
            )

            # 直近成績
            df_features = self.extract_recent_performance(
                df_features, performance_history, entity_column, date_column
            )

            # コース別成績
            df_features = self.extract_course_performance(
                df_features, performance_history, entity_column, date_column
            )

            # 距離別成績
            df_features = self.extract_distance_performance(
                df_features, performance_history, entity_column, date_column
            )

            # 馬場状態別成績
            df_features = self.extract_track_condition_performance(
                df_features, performance_history, entity_column, date_column
            )

            logger.info(f"✅ 過去成績特徴量抽出完了: 合計{self.feature_count}個の特徴量を生成")
            logger.info(f"生成された特徴量: {self.feature_names}")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"全過去成績特徴量抽出中にエラーが発生しました: {e!s}"
            ) from e

    def get_feature_info(self) -> dict[str, any]:
        """特徴量サマリー情報を取得

        Returns:
            特徴量の統計情報辞書
        """
        return {
            "feature_names": self.feature_names,
            "feature_count": self.feature_count,
            "categories": {
                "career": "通算成績特徴量",
                "recent": "直近成績特徴量",
                "course": "コース別成績特徴量",
                "distance": "距離別成績特徴量",
                "track_condition": "馬場状態別成績特徴量",
            },
        }
