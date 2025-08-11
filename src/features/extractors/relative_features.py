"""相対特徴量抽出機能

他馬との能力差、オッズベースの特徴量、人気順位などを抽出する
"""

import numpy as np
import pandas as pd
from loguru import logger

from src.core.exceptions import FeatureExtractionError


class RelativeFeatureExtractor:
    """相対特徴量を抽出するクラス"""

    def __init__(self):
        """初期化"""
        self.feature_names = []
        self.feature_count = 0  # 特徴量カウント管理

    def extract_relative_performance_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """他馬との相対的な能力差特徴量

        Args:
            df: 現在のレースデータ(同一レースの全馬データ)

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("相対能力差特徴量抽出開始")

        try:
            df_features = df.copy()

            if "race_id" not in df.columns:
                logger.warning("race_idがないため、相対特徴量をスキップします")
                return df_features

            relative_features = []

            # 各レースごとに処理
            for race_id, race_group in df.groupby("race_id"):
                # 比較する指標のリスト
                metrics = {
                    "career_win_rate": "通算勝率",
                    "career_avg_finish": "平均着順",
                    "recent5_avg_finish": "直近5走平均着順",
                    "same_distance_win_rate": "同距離勝率",
                    "sire_win_rate": "父馬産駒勝率",
                }

                for idx in race_group.index:
                    features = {}

                    for metric, name in metrics.items():
                        if metric in race_group.columns:
                            own_value = race_group.loc[idx, metric]

                            if pd.notna(own_value):
                                # 自分以外の馬の値
                                others = race_group[race_group.index != idx][
                                    metric
                                ].dropna()

                                if len(others) > 0:
                                    # 相対的な指標
                                    features[f"{metric}_vs_avg"] = (
                                        own_value - others.mean()
                                    )
                                    features[f"{metric}_vs_best"] = (
                                        own_value - others.min()
                                        if "finish" in metric
                                        else own_value - others.max()
                                    )
                                    features[f"{metric}_rank"] = (
                                        (race_group[metric] >= own_value).sum()
                                        if "finish" not in metric
                                        else (race_group[metric] <= own_value).sum()
                                    )
                                    features[f"{metric}_percentile"] = features[
                                        f"{metric}_rank"
                                    ] / len(race_group)

                                    # 標準偏差で正規化した差
                                    if others.std() > 0:
                                        features[f"{metric}_zscore"] = (
                                            own_value - others.mean()
                                        ) / others.std()
                                    else:
                                        features[f"{metric}_zscore"] = 0

                    # 総合的な相対強度
                    if (
                        "career_win_rate" in race_group.columns
                        and "recent5_avg_finish" in race_group.columns
                    ):
                        # 複数の指標を組み合わせた総合スコア
                        win_rate_rank = features.get(
                            "career_win_rate_rank", len(race_group) / 2
                        )
                        finish_rank = features.get(
                            "recent5_avg_finish_rank", len(race_group) / 2
                        )

                        features["composite_strength_score"] = (
                            (len(race_group) - win_rate_rank + 1) * 0.6
                            + (len(race_group) - finish_rank + 1) * 0.4
                        ) / len(race_group)

                    relative_features.append(features)

            if relative_features:
                relative_df = pd.DataFrame(relative_features, index=df.index)
                df_features = pd.concat([df_features, relative_df], axis=1)
                self.feature_names.extend(relative_df.columns.tolist())
                self.feature_count += len(relative_df.columns)

            logger.info("相対能力差特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(f"相対能力差特徴量抽出中にエラーが発生しました: {e!s}") from e

    def extract_odds_based_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """オッズベースの特徴量抽出

        Args:
            df: 現在のレースデータ

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("オッズベース特徴量抽出開始")

        try:
            df_features = df.copy()

            if "odds" not in df.columns:
                logger.warning("オッズ情報がないため、オッズ特徴量をスキップします")
                return df_features

            # 基本的なオッズ特徴量
            df_features["odds_log"] = np.log1p(df["odds"])
            df_features["implied_win_probability"] = 1 / (df["odds"] + 1)

            # 人気順位
            if "race_id" in df.columns:
                df_features["popularity_rank"] = df.groupby("race_id")["odds"].rank(
                    method="min"
                )
                df_features["is_favorite"] = (
                    df_features["popularity_rank"] == 1
                ).astype(int)
                df_features["is_top3_favorite"] = (
                    df_features["popularity_rank"] <= 3
                ).astype(int)
                df_features["is_top5_favorite"] = (
                    df_features["popularity_rank"] <= 5
                ).astype(int)

                # 人気カテゴリ
                df_features["popularity_category"] = pd.cut(
                    df_features["popularity_rank"],
                    bins=[0, 1, 3, 5, 9, 100],
                    labels=["favorite", "top3", "top5", "middle", "longshot"],
                )

                # レースごとのオッズ統計
                odds_stats = df.groupby("race_id")["odds"].agg(
                    ["mean", "std", "min", "max"]
                )
                df_features = df_features.merge(
                    odds_stats,
                    left_on="race_id",
                    right_index=True,
                    suffixes=("", "_race"),
                )

                # 相対オッズ
                df_features["relative_odds"] = df_features["odds"] / df_features["mean"]
                df_features["odds_deviation"] = (
                    df_features["odds"] - df_features["mean"]
                ) / df_features["std"]

                # オッズの歪み(能力との乖離)
                if "career_win_rate" in df.columns:
                    # 実際の勝率とオッズから計算される期待勝率の差
                    df_features["odds_value_gap"] = (
                        df["career_win_rate"] - df_features["implied_win_probability"]
                    )
                    # 過小評価されている馬
                    df_features["is_undervalued"] = (
                        df_features["odds_value_gap"] > 0.05
                    ).astype(int)
                    # 過大評価されている馬
                    df_features["is_overvalued"] = (
                        df_features["odds_value_gap"] < -0.05
                    ).astype(int)

            # 複勝オッズ関連(もしあれば)
            if "place_odds_min" in df.columns and "place_odds_max" in df.columns:
                df_features["place_odds_range"] = (
                    df["place_odds_max"] - df["place_odds_min"]
                )
                df_features["place_odds_mid"] = (
                    df["place_odds_min"] + df["place_odds_max"]
                ) / 2
                df_features["implied_place_probability"] = 1 / (
                    df_features["place_odds_mid"] + 1
                )

            odds_features = [
                "odds_log",
                "implied_win_probability",
                "popularity_rank",
                "is_favorite",
                "is_top3_favorite",
                "is_top5_favorite",
                "relative_odds",
                "odds_deviation",
            ]
            self.feature_names.extend(odds_features)
            self.feature_count += len(odds_features)

            if "career_win_rate" in df.columns:
                value_features = ["odds_value_gap", "is_undervalued", "is_overvalued"]
                self.feature_names.extend(value_features)
                self.feature_count += len(value_features)

            logger.info("オッズベース特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(f"オッズベース特徴量抽出中にエラーが発生しました: {e!s}") from e

    def extract_jockey_trainer_relative_features(
        self, df: pd.DataFrame
    ) -> pd.DataFrame:
        """騎手・調教師の相対的な特徴量

        Args:
            df: 現在のレースデータ

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("騎手・調教師相対特徴量抽出開始")

        try:
            df_features = df.copy()

            if "race_id" not in df.columns:
                return df_features

            relative_features = []

            for race_id, race_group in df.groupby("race_id"):
                # 騎手の相対評価
                if "jockey_win_rate" in race_group.columns:
                    jockey_rates = race_group["jockey_win_rate"].dropna()

                    for idx in race_group.index:
                        features = {}

                        if pd.notna(race_group.loc[idx, "jockey_win_rate"]):
                            own_rate = race_group.loc[idx, "jockey_win_rate"]

                            # このレースで最も勝率の高い騎手か
                            features["has_top_jockey"] = (
                                own_rate == jockey_rates.max()
                            ).astype(int)
                            # 騎手勝率ランク
                            features["jockey_rank_in_race"] = (
                                jockey_rates >= own_rate
                            ).sum()
                            # 相対的な騎手の強さ
                            features["jockey_relative_strength"] = (
                                own_rate / jockey_rates.mean()
                                if jockey_rates.mean() > 0
                                else 1
                            )

                        # 調教師の相対評価
                        if "trainer_win_rate" in race_group.columns and pd.notna(
                            race_group.loc[idx, "trainer_win_rate"]
                        ):
                            trainer_rates = race_group["trainer_win_rate"].dropna()
                            own_rate = race_group.loc[idx, "trainer_win_rate"]

                            features["has_top_trainer"] = (
                                own_rate == trainer_rates.max()
                            ).astype(int)
                            features["trainer_rank_in_race"] = (
                                trainer_rates >= own_rate
                            ).sum()
                            features["trainer_relative_strength"] = (
                                own_rate / trainer_rates.mean()
                                if trainer_rates.mean() > 0
                                else 1
                            )

                        relative_features.append(features)

            if relative_features:
                relative_df = pd.DataFrame(relative_features, index=df.index)
                df_features = pd.concat([df_features, relative_df], axis=1)
                self.feature_names.extend(relative_df.columns.tolist())
                self.feature_count += len(relative_df.columns)

            logger.info("騎手・調教師相対特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(f"騎手・調教師相対特徴量抽出中にエラーが発生しました: {e!s}") from e

    def extract_position_relative_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """枠順・馬番の相対的な特徴量

        Args:
            df: 現在のレースデータ

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("枠順相対特徴量抽出開始")

        try:
            df_features = df.copy()

            if "post_position" not in df.columns or "race_id" not in df.columns:
                return df_features

            position_features = []

            for race_id, race_group in df.groupby("race_id"):
                field_size = len(race_group)

                for idx in race_group.index:
                    features = {}
                    position = race_group.loc[idx, "post_position"]

                    # 相対的な枠順位置(0-1で正規化)
                    features["normalized_position"] = (
                        (position - 1) / (field_size - 1) if field_size > 1 else 0.5
                    )

                    # 中央からの距離
                    center = (field_size + 1) / 2
                    features["distance_from_center"] = abs(position - center) / center

                    # 内枠率・外枠率
                    features["inner_position_ratio"] = (
                        field_size - position + 1
                    ) / field_size
                    features["outer_position_ratio"] = position / field_size

                    # 隣接馬との能力差
                    if "career_win_rate" in race_group.columns:
                        sorted_group = race_group.sort_values("post_position")
                        pos_idx = sorted_group.index.get_loc(idx)

                        own_win_rate = race_group.loc[idx, "career_win_rate"]

                        if pd.notna(own_win_rate):
                            # 内側の馬との差
                            if pos_idx > 0:
                                inner_idx = sorted_group.index[pos_idx - 1]
                                inner_win_rate = race_group.loc[
                                    inner_idx, "career_win_rate"
                                ]
                                if pd.notna(inner_win_rate):
                                    features["win_rate_diff_inner"] = (
                                        own_win_rate - inner_win_rate
                                    )

                            # 外側の馬との差
                            if pos_idx < field_size - 1:
                                outer_idx = sorted_group.index[pos_idx + 1]
                                outer_win_rate = race_group.loc[
                                    outer_idx, "career_win_rate"
                                ]
                                if pd.notna(outer_win_rate):
                                    features["win_rate_diff_outer"] = (
                                        own_win_rate - outer_win_rate
                                    )

                    position_features.append(features)

            if position_features:
                position_df = pd.DataFrame(position_features, index=df.index)
                df_features = pd.concat([df_features, position_df], axis=1)
                self.feature_names.extend(position_df.columns.tolist())
                self.feature_count += len(position_df.columns)

            logger.info("枠順相対特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(f"枠順相対特徴量抽出中にエラーが発生しました: {e!s}") from e

    def extract_pace_relative_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """ペース・脚質の相対的な特徴量

        Args:
            df: 現在のレースデータ

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("ペース相対特徴量抽出開始")

        try:
            df_features = df.copy()

            if "running_style" not in df.columns or "race_id" not in df.columns:
                return df_features

            pace_features = []

            for race_id, race_group in df.groupby("race_id"):
                # 脚質分布
                style_counts = race_group["running_style"].value_counts()
                total_horses = len(race_group)

                style_ratios = {
                    "front_runner_ratio": style_counts.get("逃げ", 0) / total_horses,
                    "stalker_ratio": style_counts.get("先行", 0) / total_horses,
                    "midfield_ratio": style_counts.get("差し", 0) / total_horses,
                    "closer_ratio": style_counts.get("追込", 0) / total_horses,
                }

                for idx in race_group.index:
                    features = style_ratios.copy()
                    own_style = race_group.loc[idx, "running_style"]

                    # 同じ脚質の馬の数
                    features["same_style_count"] = (
                        style_counts.get(own_style, 0) - 1
                    )  # 自分を除く
                    features["same_style_ratio"] = features["same_style_count"] / (
                        total_horses - 1
                    )

                    # 脚質の競合度
                    if own_style == "逃げ":
                        features["style_competition"] = features["front_runner_ratio"]
                        features["is_sole_front_runner"] = (
                            features["same_style_count"] == 0
                        ).astype(int)
                    elif own_style == "先行":
                        features["style_competition"] = (
                            features["front_runner_ratio"] + features["stalker_ratio"]
                        )
                    elif own_style == "差し":
                        features["style_competition"] = features["midfield_ratio"]
                    else:  # 追込
                        features["style_competition"] = features["closer_ratio"]

                    # ペースに対する適性
                    expected_pace = race_group.iloc[0].get("predicted_pace", "medium")
                    if expected_pace == "fast" and own_style in ["差し", "追込"]:
                        features["pace_style_match"] = 1  # ハイペースは差し・追込有利
                    elif expected_pace == "slow" and own_style in ["逃げ", "先行"]:
                        features["pace_style_match"] = 1  # スローペースは逃げ・先行有利
                    else:
                        features["pace_style_match"] = 0.5

                    pace_features.append(features)

            if pace_features:
                pace_df = pd.DataFrame(pace_features, index=df.index)
                df_features = pd.concat([df_features, pace_df], axis=1)
                self.feature_names.extend(pace_df.columns.tolist())
                self.feature_count += len(pace_df.columns)

            logger.info("ペース相対特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(f"ペース相対特徴量抽出中にエラーが発生しました: {e!s}") from e

    def extract_all_relative_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """全ての相対特徴量を抽出

        Args:
            df: 現在のレースデータ(同一レースの全馬データ)

        Returns:
            全特徴量追加後のデータフレーム
        """
        logger.info("全相対特徴量抽出開始")

        try:
            # 相対的な能力差特徴量
            df_features = self.extract_relative_performance_features(df)

            # オッズベース特徴量
            df_features = self.extract_odds_based_features(df_features)

            # 騎手・調教師相対特徴量
            df_features = self.extract_jockey_trainer_relative_features(df_features)

            # 枠順相対特徴量
            df_features = self.extract_position_relative_features(df_features)

            # ペース相対特徴量
            df_features = self.extract_pace_relative_features(df_features)

            logger.info(f"✅ 相対特徴量抽出完了: 合計{self.feature_count}個の特徴量を生成")
            logger.info(f"生成された特徴量: {self.feature_names}")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(f"全相対特徴量抽出中にエラーが発生しました: {e!s}") from e

    def get_feature_info(self) -> dict[str, any]:
        """特徴量サマリー情報を取得

        Returns:
            特徴量の統計情報辞書
        """
        return {
            "feature_names": self.feature_names,
            "feature_count": self.feature_count,
            "categories": {
                "relative_performance": "相対能力差特徴量",
                "odds_based": "オッズベース特徴量",
                "jockey_trainer_relative": "騎手・調教師相対特徴量",
                "position_relative": "枠順相対特徴量",
                "pace_relative": "ペース相対特徴量",
            },
        }
