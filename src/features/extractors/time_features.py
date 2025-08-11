"""タイム特徴量抽出モジュール

走破タイム、上がりタイム、スピード指数など時間関連の特徴量を生成する。
基本タイム特徴量20個を実装。
"""

import numpy as np
import pandas as pd
from loguru import logger

# from src.core.exceptions import FeatureExtractionError


class FeatureExtractionError(Exception):
    """特徴量抽出エラー"""

    pass


class TimeFeatureExtractor:
    """タイム特徴量を抽出するクラス

    Phase1の基本タイム特徴量20個を実装。
    走破タイム、上がり3F、スピード指数などを計算。
    """

    def __init__(self):
        """初期化"""
        self.feature_names = []
        self.feature_count = 0

        # 基準タイム定義（距離別・コース別）
        self.base_times = {
            # 芝コース基準タイム（秒）
            "turf": {
                1000: 55.0,
                1200: 68.0,
                1400: 82.0,
                1600: 94.0,
                1800: 107.0,
                2000: 120.0,
                2200: 133.0,
                2400: 146.0,
                2500: 153.0,
                3000: 185.0,
                3200: 198.0,
                3600: 224.0,
            },
            # ダートコース基準タイム（秒）
            "dirt": {
                1000: 57.0,
                1200: 70.0,
                1400: 84.0,
                1600: 96.0,
                1700: 103.0,
                1800: 110.0,
                2000: 123.0,
                2100: 130.0,
                2400: 150.0,
            },
        }

    def extract_race_time_features(
        self, df: pd.DataFrame, history_df: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """走破タイム特徴量（10個）

        Args:
            df: レースデータ
            history_df: 過去成績データ（タイム情報含む）

        Returns:
            特徴量を追加したデータフレーム
        """
        logger.info("走破タイム特徴量の抽出開始")
        df_features = df.copy()

        # 前走タイム
        if history_df is not None and "race_time" in history_df.columns:
            for horse_id in df["horse_id"].unique():
                horse_history = history_df[
                    history_df["horse_id"] == horse_id
                ].sort_values("race_date", ascending=False)

                if len(horse_history) > 0:
                    # 前走タイム（秒換算）
                    last_time = self._time_to_seconds(
                        horse_history.iloc[0]["race_time"]
                    )
                    df_features.loc[
                        df_features["horse_id"] == horse_id, "last_race_time"
                    ] = last_time

                    # 過去3走・5走平均タイム
                    for n_races in [3, 5]:
                        recent_times = horse_history.head(n_races)["race_time"].apply(
                            self._time_to_seconds
                        )
                        if len(recent_times) > 0:
                            df_features.loc[
                                df_features["horse_id"] == horse_id,
                                f"avg_time_last{n_races}",
                            ] = recent_times.mean()

                    # 同距離ベストタイム
                    if "distance" in df.columns and "distance" in horse_history.columns:
                        current_distance = df[df["horse_id"] == horse_id][
                            "distance"
                        ].iloc[0]
                        same_distance = horse_history[
                            horse_history["distance"] == current_distance
                        ]
                        if len(same_distance) > 0:
                            best_time = (
                                same_distance["race_time"]
                                .apply(self._time_to_seconds)
                                .min()
                            )
                            df_features.loc[
                                df_features["horse_id"] == horse_id,
                                "best_time_at_distance",
                            ] = best_time

                    # タイム指数（基準タイムとの比較）
                    if "distance" in df.columns and "track_type" in df.columns:
                        current_distance = df[df["horse_id"] == horse_id][
                            "distance"
                        ].iloc[0]
                        current_track = df[df["horse_id"] == horse_id][
                            "track_type"
                        ].iloc[0]

                        base_time = self._get_base_time(current_distance, current_track)
                        if base_time and last_time:
                            time_index = (base_time / last_time) * 100
                            df_features.loc[
                                df_features["horse_id"] == horse_id, "time_index"
                            ] = time_index

                    # スピード指数（距離・馬場補正）
                    if len(horse_history) >= 3:
                        speed_figures = []
                        for _, race in horse_history.head(5).iterrows():
                            if "race_time" in race and "distance" in race:
                                time_sec = self._time_to_seconds(race["race_time"])
                                distance = race["distance"]
                                track = race.get("track_type", "turf")

                                # スピード指数 = (距離 / タイム) * 補正係数
                                if time_sec > 0:
                                    speed = (
                                        distance / time_sec
                                    ) * self._get_track_correction(track)
                                    speed_figures.append(speed)

                        if speed_figures:
                            df_features.loc[
                                df_features["horse_id"] == horse_id, "speed_figure"
                            ] = np.mean(speed_figures)

                    # 基準タイムとの差
                    if base_time and last_time:
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "time_deviation"
                        ] = (last_time - base_time)

                    # 距離補正タイム
                    if "distance" in horse_history.columns:
                        normalized_times = []
                        for _, race in horse_history.head(5).iterrows():
                            if "race_time" in race and "distance" in race:
                                time_sec = self._time_to_seconds(race["race_time"])
                                distance = race["distance"]
                                # 1600mに正規化
                                normalized_time = time_sec * (1600 / distance)
                                normalized_times.append(normalized_time)

                        if normalized_times:
                            df_features.loc[
                                df_features["horse_id"] == horse_id, "normalized_time"
                            ] = np.mean(normalized_times)

                    # 馬場補正タイム
                    if "track_condition" in horse_history.columns:
                        adjusted_times = []
                        for _, race in horse_history.head(5).iterrows():
                            if "race_time" in race and "track_condition" in race:
                                time_sec = self._time_to_seconds(race["race_time"])
                                condition = race["track_condition"]
                                # 馬場状態による補正
                                adjusted_time = (
                                    time_sec * self._get_condition_correction(condition)
                                )
                                adjusted_times.append(adjusted_time)

                        if adjusted_times:
                            df_features.loc[
                                df_features["horse_id"] == horse_id,
                                "track_adjusted_time",
                            ] = np.mean(adjusted_times)

                    # 相対タイムスコア（同レース内での相対評価）
                    if "race_id" in horse_history.columns:
                        relative_scores = []
                        for race_id in horse_history.head(5)["race_id"]:
                            race_data = history_df[history_df["race_id"] == race_id]
                            if len(race_data) > 1:
                                race_times = race_data["race_time"].apply(
                                    self._time_to_seconds
                                )
                                horse_time = (
                                    race_data[race_data["horse_id"] == horse_id][
                                        "race_time"
                                    ]
                                    .apply(self._time_to_seconds)
                                    .iloc[0]
                                )

                                # 相対スコア = (平均タイム / 自身のタイム) * 100
                                if horse_time > 0:
                                    relative_score = (
                                        race_times.mean() / horse_time
                                    ) * 100
                                    relative_scores.append(relative_score)

                        if relative_scores:
                            df_features.loc[
                                df_features["horse_id"] == horse_id,
                                "relative_time_score",
                            ] = np.mean(relative_scores)

        # デフォルト値の設定
        time_features = [
            "last_race_time",
            "avg_time_last3",
            "avg_time_last5",
            "best_time_at_distance",
            "time_index",
            "speed_figure",
            "time_deviation",
            "normalized_time",
            "track_adjusted_time",
            "relative_time_score",
        ]

        for feat in time_features:
            if feat not in df_features.columns:
                df_features[feat] = 0
            else:
                df_features[feat] = df_features[feat].fillna(0)

        self.feature_names.extend(time_features)
        self.feature_count += 10
        logger.info("走破タイム特徴量10個を追加")

        return df_features

    def extract_last3f_features(
        self, df: pd.DataFrame, history_df: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """上がり3Fタイム特徴量（10個）

        Args:
            df: レースデータ
            history_df: 過去成績データ（上がりタイム情報含む）

        Returns:
            特徴量を追加したデータフレーム
        """
        logger.info("上がり3Fタイム特徴量の抽出開始")
        df_features = df.copy()

        if history_df is not None and "last_3f" in history_df.columns:
            for horse_id in df["horse_id"].unique():
                horse_history = history_df[
                    history_df["horse_id"] == horse_id
                ].sort_values("race_date", ascending=False)

                if len(horse_history) > 0:
                    # 前走上がり3F
                    last_3f = horse_history.iloc[0]["last_3f"]
                    df_features.loc[
                        df_features["horse_id"] == horse_id, "last_3f_time"
                    ] = last_3f

                    # 過去3走・5走平均上がり3F
                    for n_races in [3, 5]:
                        recent_3f = horse_history.head(n_races)["last_3f"]
                        if len(recent_3f) > 0:
                            df_features.loc[
                                df_features["horse_id"] == horse_id,
                                f"avg_last3f_last{n_races}",
                            ] = recent_3f.mean()

                    # ベスト上がり3F
                    best_3f = horse_history["last_3f"].min()
                    df_features.loc[
                        df_features["horse_id"] == horse_id, "best_last3f"
                    ] = best_3f

                    # 前走上がり順位
                    if "last_3f_rank" in horse_history.columns:
                        last_rank = horse_history.iloc[0]["last_3f_rank"]
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "last3f_rank"
                        ] = last_rank

                        # 平均上がり順位
                        avg_rank = horse_history.head(5)["last_3f_rank"].mean()
                        df_features.loc[
                            df_features["horse_id"] == horse_id, "avg_last3f_rank"
                        ] = avg_rank

                    # 上がり改善度（直近の変化）
                    if len(horse_history) >= 2:
                        recent_3f = horse_history.head(3)["last_3f"].values
                        if len(recent_3f) >= 2:
                            improvement = recent_3f[1] - recent_3f[0]  # 改善はマイナス
                            df_features.loc[
                                df_features["horse_id"] == horse_id,
                                "last3f_improvement",
                            ] = improvement

                    # 上がり安定性（変動係数）
                    if len(horse_history) >= 3:
                        recent_3f = horse_history.head(5)["last_3f"]
                        if recent_3f.mean() > 0:
                            cv = recent_3f.std() / recent_3f.mean()
                            df_features.loc[
                                df_features["horse_id"] == horse_id,
                                "last3f_consistency",
                            ] = 1 / (
                                1 + cv
                            )  # 安定性スコア

                    # 相対上がりタイム（同レース内での比較）
                    if "race_id" in horse_history.columns:
                        relative_3f = []
                        for race_id in horse_history.head(5)["race_id"]:
                            race_data = history_df[history_df["race_id"] == race_id]
                            if len(race_data) > 1 and "last_3f" in race_data.columns:
                                race_3f = race_data["last_3f"]
                                horse_3f = race_data[race_data["horse_id"] == horse_id][
                                    "last_3f"
                                ].iloc[0]

                                # 相対値 = 平均との差
                                relative = race_3f.mean() - horse_3f
                                relative_3f.append(relative)

                        if relative_3f:
                            df_features.loc[
                                df_features["horse_id"] == horse_id, "relative_last3f"
                            ] = np.mean(relative_3f)

                    # 上がりパーセンタイル（全体での位置）
                    if len(horse_history) >= 10:
                        all_3f = horse_history["last_3f"].dropna()
                        if len(all_3f) > 0 and last_3f:
                            percentile = (all_3f > last_3f).mean() * 100
                            df_features.loc[
                                df_features["horse_id"] == horse_id, "last3f_percentile"
                            ] = percentile

        # デフォルト値の設定
        last3f_features = [
            "last_3f_time",
            "avg_last3f_last3",
            "avg_last3f_last5",
            "best_last3f",
            "last3f_rank",
            "avg_last3f_rank",
            "last3f_improvement",
            "last3f_consistency",
            "relative_last3f",
            "last3f_percentile",
        ]

        for feat in last3f_features:
            if feat not in df_features.columns:
                df_features[feat] = 0
            else:
                df_features[feat] = df_features[feat].fillna(0)

        self.feature_names.extend(last3f_features)
        self.feature_count += 10
        logger.info("上がり3Fタイム特徴量10個を追加")

        return df_features

    def extract_all_time_features(
        self, df: pd.DataFrame, history_df: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """全タイム特徴量を抽出（20個）

        Args:
            df: レースデータ
            history_df: 過去成績データ

        Returns:
            全特徴量を追加したデータフレーム
        """
        logger.info("========== タイム特徴量抽出開始 ==========")

        try:
            # 走破タイム特徴量（10個）
            df_features = self.extract_race_time_features(df, history_df)

            # 上がり3Fタイム特徴量（10個）
            df_features = self.extract_last3f_features(df_features, history_df)

            logger.info(f"✅ タイム特徴量抽出完了: 合計{self.feature_count}個の特徴量を生成")
            logger.info(f"生成された特徴量: {self.feature_names}")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(f"タイム特徴量抽出中にエラーが発生しました: {e!s}") from e

    def _time_to_seconds(self, time_str: str) -> float:
        """タイム文字列を秒に変換

        Args:
            time_str: タイム文字列（例: "1:23.4"）

        Returns:
            秒数
        """
        if pd.isna(time_str) or time_str == "":
            return 0

        try:
            # "1:23.4" -> 83.4秒
            if isinstance(time_str, str):
                if ":" in time_str:
                    parts = time_str.split(":")
                    minutes = int(parts[0])
                    seconds = float(parts[1])
                    return minutes * 60 + seconds
                return float(time_str)
            return float(time_str)
        except:
            return 0

    def _get_base_time(self, distance: int, track_type: str) -> float:
        """基準タイムを取得

        Args:
            distance: 距離
            track_type: コース種別（turf/dirt）

        Returns:
            基準タイム（秒）
        """
        if track_type not in self.base_times:
            track_type = "turf"  # デフォルト

        times = self.base_times[track_type]

        # 最も近い距離の基準タイムを取得
        if distance in times:
            return times[distance]
        # 線形補間
        distances = sorted(times.keys())
        for i in range(len(distances) - 1):
            if distances[i] < distance < distances[i + 1]:
                d1, d2 = distances[i], distances[i + 1]
                t1, t2 = times[d1], times[d2]
                # 線形補間
                ratio = (distance - d1) / (d2 - d1)
                return t1 + ratio * (t2 - t1)

        # 範囲外の場合は最も近い値
        if distance < distances[0]:
            return times[distances[0]]
        return times[distances[-1]]

    def _get_track_correction(self, track_type: str) -> float:
        """コース種別による補正係数

        Args:
            track_type: コース種別

        Returns:
            補正係数
        """
        corrections = {
            "turf": 1.0,
            "dirt": 0.95,  # ダートは少し遅い
        }
        return corrections.get(track_type, 1.0)

    def _get_condition_correction(self, condition: str) -> float:
        """馬場状態による補正係数

        Args:
            condition: 馬場状態

        Returns:
            補正係数
        """
        corrections = {
            "firm": 0.98,  # 良馬場は速い
            "good": 1.0,  # 標準
            "yielding": 1.02,  # 稍重は少し遅い
            "soft": 1.04,  # 重は遅い
            "heavy": 1.06,  # 不良は最も遅い
        }
        return corrections.get(condition, 1.0)

    def get_feature_info(self) -> dict[str, any]:
        """特徴量情報の取得

        Returns:
            特徴量の情報辞書
        """
        return {
            "feature_names": self.feature_names,
            "feature_count": self.feature_count,
            "categories": {"race_time": 10, "last_3f": 10},
        }
