"""データ集計処理機能

馬別、騎手別、調教師別、コース別の成績集計を行う
"""

from datetime import timedelta

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy.orm import Session

from src.core.exceptions import DataProcessingError


class DataAggregator:
    """データ集計処理を行うクラス"""

    def __init__(self, session: Optional[Session] = None):
        """初期化

        Args:
            session: SQLAlchemyセッション(DBから直接集計する場合)
        """
        self.session = session
        self.aggregation_cache = {}

    def aggregate_horse_performance(
        self,
        df: pd.DataFrame,
        horse_id_column: str = "horse_id",
        result_columns: Optional[Dict[str, str]] = None,
        group_by: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """馬別成績集計

        Args:
            df: レース結果データフレーム
            horse_id_column: 馬IDカラム名
            result_columns: 集計対象カラムの辞書
            group_by: 追加のグループ化カラム(コース、距離など)

        Returns:
            馬別成績集計結果
        """
        if result_columns is None:
            result_columns = {
                "finish_position": "着順",
                "prize_money": "賞金",
                "race_time": "タイム",
            }

        logger.info(f"馬別成績集計開始: 馬数={df[horse_id_column].nunique()}")

        try:
            # グループ化キー
            group_keys = [horse_id_column]
            if group_by:
                group_keys.extend(group_by)

            # 集計処理
            aggregations = {}

            if "finish_position" in result_columns:
                col = result_columns["finish_position"]
                aggregations[f"{col}_count"] = (col, "count")  # 出走回数
                aggregations[f"{col}_win"] = (col, lambda x: (x == 1).sum())  # 勝利数
                aggregations[f"{col}_place"] = (col, lambda x: (x <= 2).sum())  # 連対数
                aggregations[f"{col}_show"] = (col, lambda x: (x <= 3).sum())  # 複勝数
                aggregations[f"{col}_avg"] = (col, "mean")  # 平均着順
                aggregations[f"{col}_std"] = (col, "std")  # 着順の標準偏差

            if "prize_money" in result_columns:
                col = result_columns["prize_money"]
                aggregations[f"{col}_sum"] = (col, "sum")  # 総賞金
                aggregations[f"{col}_avg"] = (col, "mean")  # 平均賞金
                aggregations[f"{col}_max"] = (col, "max")  # 最高賞金

            if "race_time" in result_columns:
                col = result_columns["race_time"]
                aggregations[f"{col}_min"] = (col, "min")  # 最速タイム
                aggregations[f"{col}_avg"] = (col, "mean")  # 平均タイム
                aggregations[f"{col}_std"] = (col, "std")  # タイムの標準偏差

            # 集計実行
            horse_stats = df.groupby(group_keys).agg(**aggregations).reset_index()

            # 勝率・連対率・複勝率の計算
            if "finish_position" in result_columns:
                col = result_columns["finish_position"]
                horse_stats[f"{col}_win_rate"] = (
                    horse_stats[f"{col}_win"] / horse_stats[f"{col}_count"]
                )
                horse_stats[f"{col}_place_rate"] = (
                    horse_stats[f"{col}_place"] / horse_stats[f"{col}_count"]
                )
                horse_stats[f"{col}_show_rate"] = (
                    horse_stats[f"{col}_show"] / horse_stats[f"{col}_count"]
                )

                # ROI(回収率)の計算(簡易版:賞金/出走回数)
                if "prize_money" in result_columns:
                    prize_col = result_columns["prize_money"]
                    horse_stats["roi"] = horse_stats[f"{prize_col}_sum"] / (
                        horse_stats[f"{col}_count"] * 100
                    )  # 100円賭けと仮定

            # キャッシュに保存
            cache_key = f"horse_{horse_id_column}_{group_by!s}"
            self.aggregation_cache[cache_key] = horse_stats

            logger.info(f"馬別成績集計完了: 集計行数={len(horse_stats)}")

            return horse_stats

        except Exception as e:
            raise DataProcessingError(
                f"馬別成績集計中にエラーが発生しました: {e!s}"
            ) from e

    def aggregate_jockey_performance(
        self,
        df: pd.DataFrame,
        jockey_id_column: str = "jockey_id",
        result_columns: Optional[Dict[str, str]] = None,
        group_by: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """騎手別成績集計

        Args:
            df: レース結果データフレーム
            jockey_id_column: 騎手IDカラム名
            result_columns: 集計対象カラムの辞書
            group_by: 追加のグループ化カラム

        Returns:
            騎手別成績集計結果
        """
        if result_columns is None:
            result_columns = {"finish_position": "着順", "prize_money": "賞金"}

        logger.info(f"騎手別成績集計開始: 騎手数={df[jockey_id_column].nunique()}")

        try:
            # グループ化キー
            group_keys = [jockey_id_column]
            if group_by:
                group_keys.extend(group_by)

            # 集計処理
            aggregations = {}

            if "finish_position" in result_columns:
                col = result_columns["finish_position"]
                aggregations[f"{col}_count"] = (col, "count")
                aggregations[f"{col}_win"] = (col, lambda x: (x == 1).sum())
                aggregations[f"{col}_place"] = (col, lambda x: (x <= 2).sum())
                aggregations[f"{col}_show"] = (col, lambda x: (x <= 3).sum())
                aggregations[f"{col}_avg"] = (col, "mean")

            if "prize_money" in result_columns:
                col = result_columns["prize_money"]
                aggregations[f"{col}_sum"] = (col, "sum")
                aggregations[f"{col}_avg"] = (col, "mean")

            # 集計実行
            jockey_stats = df.groupby(group_keys).agg(**aggregations).reset_index()

            # 勝率等の計算
            if "finish_position" in result_columns:
                col = result_columns["finish_position"]
                jockey_stats[f"{col}_win_rate"] = (
                    jockey_stats[f"{col}_win"] / jockey_stats[f"{col}_count"]
                )
                jockey_stats[f"{col}_place_rate"] = (
                    jockey_stats[f"{col}_place"] / jockey_stats[f"{col}_count"]
                )
                jockey_stats[f"{col}_show_rate"] = (
                    jockey_stats[f"{col}_show"] / jockey_stats[f"{col}_count"]
                )

            logger.info(f"騎手別成績集計完了: 集計行数={len(jockey_stats)}")

            return jockey_stats

        except Exception as e:
            raise DataProcessingError(
                f"騎手別成績集計中にエラーが発生しました: {e!s}"
            ) from e

    def aggregate_trainer_performance(
        self,
        df: pd.DataFrame,
        trainer_id_column: str = "trainer_id",
        result_columns: Optional[Dict[str, str]] = None,
        group_by: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """調教師別成績集計

        Args:
            df: レース結果データフレーム
            trainer_id_column: 調教師IDカラム名
            result_columns: 集計対象カラムの辞書
            group_by: 追加のグループ化カラム

        Returns:
            調教師別成績集計結果
        """
        if result_columns is None:
            result_columns = {"finish_position": "着順", "prize_money": "賞金"}

        logger.info(f"調教師別成績集計開始: 調教師数={df[trainer_id_column].nunique()}")

        try:
            # グループ化キー
            group_keys = [trainer_id_column]
            if group_by:
                group_keys.extend(group_by)

            # 集計処理
            aggregations = {}

            if "finish_position" in result_columns:
                col = result_columns["finish_position"]
                aggregations[f"{col}_count"] = (col, "count")
                aggregations[f"{col}_win"] = (col, lambda x: (x == 1).sum())
                aggregations[f"{col}_place"] = (col, lambda x: (x <= 2).sum())
                aggregations[f"{col}_show"] = (col, lambda x: (x <= 3).sum())
                aggregations[f"{col}_avg"] = (col, "mean")

            if "prize_money" in result_columns:
                col = result_columns["prize_money"]
                aggregations[f"{col}_sum"] = (col, "sum")
                aggregations[f"{col}_avg"] = (col, "mean")

            # 集計実行
            trainer_stats = df.groupby(group_keys).agg(**aggregations).reset_index()

            # 勝率等の計算
            if "finish_position" in result_columns:
                col = result_columns["finish_position"]
                trainer_stats[f"{col}_win_rate"] = (
                    trainer_stats[f"{col}_win"] / trainer_stats[f"{col}_count"]
                )
                trainer_stats[f"{col}_place_rate"] = (
                    trainer_stats[f"{col}_place"] / trainer_stats[f"{col}_count"]
                )
                trainer_stats[f"{col}_show_rate"] = (
                    trainer_stats[f"{col}_show"] / trainer_stats[f"{col}_count"]
                )

            logger.info(f"調教師別成績集計完了: 集計行数={len(trainer_stats)}")

            return trainer_stats

        except Exception as e:
            raise DataProcessingError(
                f"調教師別成績集計中にエラーが発生しました: {e!s}"
            ) from e

    def aggregate_course_performance(
        self,
        df: pd.DataFrame,
        course_columns: Dict[str, str],
        result_columns: Optional[Dict[str, str]] = None,
        group_by: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """コース別成績集計

        Args:
            df: レース結果データフレーム
            course_columns: コース関連カラムの辞書(場所、距離、馬場など)
            result_columns: 集計対象カラムの辞書
            group_by: 追加のグループ化カラム

        Returns:
            コース別成績集計結果
        """
        if result_columns is None:
            result_columns = {"finish_position": "着順", "race_time": "タイム"}

        logger.info("コース別成績集計開始")

        try:
            # グループ化キー
            group_keys = list(course_columns.values())
            if group_by:
                group_keys.extend(group_by)

            # 集計処理
            aggregations = {}

            if "finish_position" in result_columns:
                col = result_columns["finish_position"]
                aggregations[f"{col}_count"] = (col, "count")
                aggregations[f"{col}_avg"] = (col, "mean")
                aggregations[f"{col}_std"] = (col, "std")

            if "race_time" in result_columns:
                col = result_columns["race_time"]
                aggregations[f"{col}_min"] = (col, "min")
                aggregations[f"{col}_avg"] = (col, "mean")
                aggregations[f"{col}_std"] = (col, "std")
                aggregations[f"{col}_q25"] = (col, lambda x: x.quantile(0.25))
                aggregations[f"{col}_q50"] = (col, lambda x: x.quantile(0.50))
                aggregations[f"{col}_q75"] = (col, lambda x: x.quantile(0.75))

            # 集計実行
            course_stats = df.groupby(group_keys).agg(**aggregations).reset_index()

            # レースレベル指標の計算
            if "race_time" in result_columns:
                col = result_columns["race_time"]
                # 標準タイムからの偏差を計算(コース別の相対的な速さ)
                course_stats[f"{col}_performance"] = (
                    course_stats[f"{col}_min"] / course_stats[f"{col}_avg"]
                )

            logger.info(f"コース別成績集計完了: 集計行数={len(course_stats)}")

            return course_stats

        except Exception as e:
            raise DataProcessingError(
                f"コース別成績集計中にエラーが発生しました: {e!s}"
            ) from e

    def aggregate_recent_performance(
        self,
        df: pd.DataFrame,
        entity_id_column: str,
        date_column: str,
        result_columns: Dict[str, str],
        n_recent: int = 5,
        days_window: Optional[int] = None,
    ) -> pd.DataFrame:
        """直近成績の集計

        Args:
            df: レース結果データフレーム
            entity_id_column: エンティティIDカラム(馬、騎手など)
            date_column: 日付カラム
            result_columns: 集計対象カラムの辞書
            n_recent: 直近N走
            days_window: 日数ウィンドウ(指定した日数以内の成績)

        Returns:
            直近成績集計結果
        """
        logger.info(f"直近成績集計開始: n_recent={n_recent}, days_window={days_window}")

        try:
            # 日付でソート
            df_sorted = df.sort_values(
                [entity_id_column, date_column], ascending=[True, False]
            )

            # 直近N走または日数ウィンドウでフィルタリング
            if days_window:
                # 日数ウィンドウでフィルタリング
                cutoff_date = df[date_column].max() - timedelta(days=days_window)
                df_filtered = df_sorted[df_sorted[date_column] >= cutoff_date]
            else:
                # 直近N走でフィルタリング
                df_filtered = df_sorted.groupby(entity_id_column).head(n_recent)

            # 集計処理
            aggregations = {}

            for key, col in result_columns.items():
                if key == "finish_position":
                    aggregations[f"{col}_recent_avg"] = (col, "mean")
                    aggregations[f"{col}_recent_best"] = (col, "min")
                    aggregations[f"{col}_recent_worst"] = (col, "max")
                    aggregations[f"{col}_recent_wins"] = (col, lambda x: (x == 1).sum())
                elif key == "race_time":
                    aggregations[f"{col}_recent_avg"] = (col, "mean")
                    aggregations[f"{col}_recent_best"] = (col, "min")
                    aggregations[f"{col}_trend"] = (
                        col,
                        lambda x: x.diff().mean(),
                    )  # タイムの改善傾向
                elif key == "prize_money":
                    aggregations[f"{col}_recent_sum"] = (col, "sum")
                    aggregations[f"{col}_recent_avg"] = (col, "mean")

            # エンティティごとに集計
            recent_stats = (
                df_filtered.groupby(entity_id_column).agg(**aggregations).reset_index()
            )

            # 連続性指標の計算(連勝・連敗など)
            if "finish_position" in result_columns:
                col = result_columns["finish_position"]

                def calc_streak(group):
                    """連続性の計算"""
                    positions = group[col].values
                    if len(positions) == 0:
                        return 0

                    # 連勝・連敗のカウント
                    current_streak = 0
                    for pos in positions:
                        if pos == 1 and current_streak >= 0:
                            current_streak += 1
                        elif pos > 3 and current_streak <= 0:
                            current_streak -= 1
                        else:
                            break

                    return current_streak

                streaks = df_filtered.groupby(entity_id_column).apply(calc_streak)
                recent_stats["win_streak"] = recent_stats[entity_id_column].map(streaks)

            logger.info(f"直近成績集計完了: 集計行数={len(recent_stats)}")

            return recent_stats

        except Exception as e:
            raise DataProcessingError(
                f"直近成績集計中にエラーが発生しました: {e!s}"
            ) from e

    def create_performance_trends(
        self,
        df: pd.DataFrame,
        entity_id_column: str,
        date_column: str,
        metric_column: str,
        window_size: int = 3,
    ) -> pd.DataFrame:
        """パフォーマンストレンドの作成

        Args:
            df: レース結果データフレーム
            entity_id_column: エンティティIDカラム
            date_column: 日付カラム
            metric_column: 指標カラム(着順、タイムなど)
            window_size: 移動平均のウィンドウサイズ

        Returns:
            トレンド特徴量を追加したデータフレーム
        """
        logger.info(f"パフォーマンストレンド作成開始: metric={metric_column}")

        try:
            df_sorted = df.sort_values([entity_id_column, date_column])

            # 移動平均
            df_sorted[f"{metric_column}_ma_{window_size}"] = df_sorted.groupby(
                entity_id_column
            )[metric_column].transform(
                lambda x: x.rolling(window=window_size, min_periods=1).mean()
            )

            # 移動標準偏差
            df_sorted[f"{metric_column}_std_{window_size}"] = df_sorted.groupby(
                entity_id_column
            )[metric_column].transform(
                lambda x: x.rolling(window=window_size, min_periods=1).std()
            )

            # トレンド(線形回帰の傾き)
            def calc_trend(x):
                if len(x) < 2:
                    return 0
                indices = np.arange(len(x))
                return np.polyfit(indices, x, 1)

            df_sorted[f"{metric_column}_trend_{window_size}"] = df_sorted.groupby(
                entity_id_column
            )[metric_column].transform(
                lambda x: x.rolling(window=window_size, min_periods=2).apply(calc_trend)
            )

            # 前回との差分
            df_sorted[f"{metric_column}_diff"] = df_sorted.groupby(entity_id_column)[
                metric_column
            ].diff()

            # 累積統計
            df_sorted[f"{metric_column}_cumsum"] = df_sorted.groupby(entity_id_column)[
                metric_column
            ].cumsum()
            df_sorted[f"{metric_column}_cumcount"] = (
                df_sorted.groupby(entity_id_column).cumcount() + 1
            )
            df_sorted[f"{metric_column}_cumavg"] = (
                df_sorted[f"{metric_column}_cumsum"]
                / df_sorted[f"{metric_column}_cumcount"]
            )

            logger.info("パフォーマンストレンド作成完了")

            return df_sorted

        except Exception as e:
            raise DataProcessingError(
                f"パフォーマンストレンド作成中にエラーが発生しました: {e!s}"
            ) from e
