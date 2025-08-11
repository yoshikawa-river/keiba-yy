"""血統特徴量抽出機能

父馬、母父馬、兄弟馬の成績、血統の距離適性などを抽出する
"""

from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from src.core.exceptions import FeatureExtractionError


class PedigreeFeatureExtractor:
    """血統特徴量を抽出するクラス"""

    def __init__(self):
        """初期化"""
        self.feature_names = []
        self.feature_count = 0  # 特徴量カウント管理
        self.important_sires = set()  # 重要な種牡馬リスト

    def extract_sire_features(
        self,
        df: pd.DataFrame,
        sire_performance: pd.DataFrame,
        horse_pedigree: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """父馬の成績特徴量抽出

        Args:
            df: 現在のレースデータ
            sire_performance: 父馬の産駒成績データ
            horse_pedigree: 馬の血統情報

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("父馬の成績特徴量抽出開始")

        try:
            df_features = df.copy()

            # 血統情報がある場合はマージ
            if horse_pedigree is not None and "sire_id" not in df.columns:
                if "horse_id" in df.columns and "horse_id" in horse_pedigree.columns:
                    df_features = df_features.merge(
                        horse_pedigree[["horse_id", "sire_id", "dam_sire_id"]],
                        on="horse_id",
                        how="left",
                    )

            sire_stats = []

            for idx, row in df.iterrows():
                sire_id = row.get("sire_id", None)
                stats = {}

                if sire_id and not pd.isna(sire_id):
                    # 父馬の産駒成績
                    sire_data = sire_performance[sire_performance["sire_id"] == sire_id]

                    if len(sire_data) > 0:
                        # 全体成績
                        stats["sire_progeny_count"] = len(sire_data)
                        stats["sire_win_count"] = (
                            sire_data["finish_position"] == 1
                        ).sum()
                        stats["sire_win_rate"] = (
                            stats["sire_win_count"] / stats["sire_progeny_count"]
                        )
                        stats["sire_place_rate"] = (
                            sire_data["finish_position"] <= 2
                        ).sum() / stats["sire_progeny_count"]
                        stats["sire_show_rate"] = (
                            sire_data["finish_position"] <= 3
                        ).sum() / stats["sire_progeny_count"]
                        stats["sire_avg_finish"] = sire_data["finish_position"].mean()
                        stats["sire_earnings_avg"] = (
                            sire_data["prize_money"].mean()
                            if "prize_money" in sire_data
                            else 0
                        )

                        # 距離別成績
                        if "distance" in row and "distance" in sire_data.columns:
                            current_distance = row["distance"]
                            # 同じ距離カテゴリでの成績
                            distance_category = self._get_distance_category(
                                current_distance
                            )
                            same_category = sire_data[
                                sire_data["distance"].apply(self._get_distance_category)
                                == distance_category
                            ]

                            if len(same_category) > 0:
                                stats[f"sire_{distance_category}_win_rate"] = (
                                    same_category["finish_position"] == 1
                                ).sum() / len(same_category)
                                stats[f"sire_{distance_category}_count"] = len(
                                    same_category
                                )

                        # コース別成績(芝・ダート)
                        if "track_type" in row and "track_type" in sire_data.columns:
                            current_track = row["track_type"]
                            same_track = sire_data[
                                sire_data["track_type"] == current_track
                            ]

                            if len(same_track) > 0:
                                stats[f"sire_{current_track}_win_rate"] = (
                                    same_track["finish_position"] == 1
                                ).sum() / len(same_track)
                                stats[f"sire_{current_track}_count"] = len(same_track)

                        # 重要種牡馬フラグ
                        if (
                            stats["sire_win_rate"] > 0.15
                            and stats["sire_progeny_count"] > 50
                        ):
                            self.important_sires.add(sire_id)
                            stats["is_important_sire"] = 1
                        else:
                            stats["is_important_sire"] = 0
                    else:
                        # 新種牡馬または産駒成績なし
                        stats = self._get_default_sire_stats()
                else:
                    # 父馬情報なし
                    stats = self._get_default_sire_stats()

                sire_stats.append(stats)

            # データフレームに結合
            if sire_stats:
                sire_df = pd.DataFrame(sire_stats, index=df.index)
                df_features = pd.concat([df_features, sire_df], axis=1)
                self.feature_names.extend(sire_df.columns.tolist())
                self.feature_count += len(sire_df.columns)

            logger.info(
                f"父馬の成績特徴量抽出完了: 特徴量数={len(sire_df.columns) if sire_stats else 0}"
            )

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"父馬の成績特徴量抽出中にエラーが発生しました: {e!s}"
            ) from e

    def extract_dam_sire_features(
        self,
        df: pd.DataFrame,
        dam_sire_performance: pd.DataFrame,
        horse_pedigree: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """母父馬の成績特徴量抽出

        Args:
            df: 現在のレースデータ
            dam_sire_performance: 母父馬の産駒成績データ
            horse_pedigree: 馬の血統情報

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("母父馬の成績特徴量抽出開始")

        try:
            df_features = df.copy()

            # 血統情報がある場合はマージ
            if horse_pedigree is not None and "dam_sire_id" not in df.columns:
                if "horse_id" in df.columns and "horse_id" in horse_pedigree.columns:
                    df_features = df_features.merge(
                        horse_pedigree[["horse_id", "dam_sire_id"]],
                        on="horse_id",
                        how="left",
                    )

            dam_sire_stats = []

            for idx, row in df.iterrows():
                dam_sire_id = row.get("dam_sire_id", None)
                stats = {}

                if dam_sire_id and not pd.isna(dam_sire_id):
                    # 母父馬の産駒成績
                    dam_sire_data = dam_sire_performance[
                        dam_sire_performance["dam_sire_id"] == dam_sire_id
                    ]

                    if len(dam_sire_data) > 0:
                        # 全体成績
                        stats["dam_sire_progeny_count"] = len(dam_sire_data)
                        stats["dam_sire_win_rate"] = (
                            dam_sire_data["finish_position"] == 1
                        ).sum() / stats["dam_sire_progeny_count"]
                        stats["dam_sire_avg_finish"] = dam_sire_data[
                            "finish_position"
                        ].mean()

                        # スタミナ指標(長距離での成績)
                        if "distance" in dam_sire_data.columns:
                            long_distance = dam_sire_data[
                                dam_sire_data["distance"] >= 2200
                            ]
                            if len(long_distance) > 0:
                                stats["dam_sire_stamina_index"] = (
                                    long_distance["finish_position"] <= 3
                                ).sum() / len(long_distance)
                            else:
                                stats["dam_sire_stamina_index"] = 0

                        # スピード指標(短距離での成績)
                        if "distance" in dam_sire_data.columns:
                            short_distance = dam_sire_data[
                                dam_sire_data["distance"] <= 1400
                            ]
                            if len(short_distance) > 0:
                                stats["dam_sire_speed_index"] = (
                                    short_distance["finish_position"] <= 3
                                ).sum() / len(short_distance)
                            else:
                                stats["dam_sire_speed_index"] = 0
                    else:
                        stats = self._get_default_dam_sire_stats()
                else:
                    stats = self._get_default_dam_sire_stats()

                dam_sire_stats.append(stats)

            # データフレームに結合
            if dam_sire_stats:
                dam_sire_df = pd.DataFrame(dam_sire_stats, index=df.index)
                df_features = pd.concat([df_features, dam_sire_df], axis=1)
                self.feature_names.extend(dam_sire_df.columns.tolist())
                self.feature_count += len(dam_sire_df.columns)

            logger.info("母父馬の成績特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"母父馬の成績特徴量抽出中にエラーが発生しました: {e!s}"
            ) from e

    def extract_sibling_features(
        self,
        df: pd.DataFrame,
        sibling_performance: pd.DataFrame,
        horse_pedigree: pd.DataFrame,
    ) -> pd.DataFrame:
        """兄弟馬の成績特徴量抽出

        Args:
            df: 現在のレースデータ
            sibling_performance: 全馬の成績データ
            horse_pedigree: 馬の血統情報(dam_id必須)

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("兄弟馬の成績特徴量抽出開始")

        try:
            df_features = df.copy()

            # 母馬情報が必要
            if "dam_id" not in horse_pedigree.columns:
                logger.warning("母馬情報がないため、兄弟馬特徴量をスキップします")
                return df_features

            # 血統情報をマージ
            if "dam_id" not in df.columns:
                df_features = df_features.merge(
                    horse_pedigree[["horse_id", "dam_id"]], on="horse_id", how="left"
                )

            sibling_stats = []

            for idx, row in df.iterrows():
                horse_id = row.get("horse_id", None)
                dam_id = row.get("dam_id", None)
                stats = {}

                if dam_id and not pd.isna(dam_id):
                    # 同じ母馬の産駒を取得(自身を除く)
                    siblings = horse_pedigree[
                        (horse_pedigree["dam_id"] == dam_id)
                        & (horse_pedigree["horse_id"] != horse_id)
                    ]["horse_id"].values

                    if len(siblings) > 0:
                        # 兄弟馬の成績
                        sibling_data = sibling_performance[
                            sibling_performance["horse_id"].isin(siblings)
                        ]

                        if len(sibling_data) > 0:
                            stats["sibling_count"] = len(siblings)
                            stats["sibling_race_count"] = len(sibling_data)
                            stats["sibling_win_count"] = (
                                sibling_data["finish_position"] == 1
                            ).sum()
                            stats["sibling_win_rate"] = (
                                stats["sibling_win_count"] / stats["sibling_race_count"]
                            )
                            stats["sibling_avg_finish"] = sibling_data[
                                "finish_position"
                            ].mean()
                            stats["sibling_earnings_total"] = (
                                sibling_data["prize_money"].sum()
                                if "prize_money" in sibling_data
                                else 0
                            )

                            # G1勝ち馬の兄弟か
                            if "race_class" in sibling_data.columns:
                                g1_wins = sibling_data[
                                    (sibling_data["race_class"] == "G1")
                                    & (sibling_data["finish_position"] == 1)
                                ]
                                stats["has_g1_winner_sibling"] = (
                                    1 if len(g1_wins) > 0 else 0
                                )
                            else:
                                stats["has_g1_winner_sibling"] = 0
                        else:
                            stats = self._get_default_sibling_stats()
                    else:
                        # 兄弟なし(初仔)
                        stats = self._get_default_sibling_stats()
                        stats["is_first_foal"] = 1
                else:
                    stats = self._get_default_sibling_stats()

                sibling_stats.append(stats)

            # データフレームに結合
            if sibling_stats:
                sibling_df = pd.DataFrame(sibling_stats, index=df.index)
                df_features = pd.concat([df_features, sibling_df], axis=1)
                self.feature_names.extend(sibling_df.columns.tolist())
                self.feature_count += len(sibling_df.columns)

            logger.info("兄弟馬の成績特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"兄弟馬の成績特徴量抽出中にエラーが発生しました: {e!s}"
            ) from e

    def extract_bloodline_affinity(
        self, df: pd.DataFrame, bloodline_cross_performance: pd.DataFrame
    ) -> pd.DataFrame:
        """血統相性特徴量の抽出

        Args:
            df: 現在のレースデータ
            bloodline_cross_performance: 血統配合の成績データ

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("血統相性特徴量抽出開始")

        try:
            df_features = df.copy()
            affinity_stats = []

            for idx, row in df.iterrows():
                sire_id = row.get("sire_id", None)
                dam_sire_id = row.get("dam_sire_id", None)
                stats = {}

                if (
                    sire_id
                    and dam_sire_id
                    and not pd.isna(sire_id)
                    and not pd.isna(dam_sire_id)
                ):
                    # 同じ配合パターンの成績
                    same_cross = bloodline_cross_performance[
                        (bloodline_cross_performance["sire_id"] == sire_id)
                        & (bloodline_cross_performance["dam_sire_id"] == dam_sire_id)
                    ]

                    if len(same_cross) > 0:
                        stats["cross_count"] = len(same_cross)
                        stats["cross_win_rate"] = (
                            same_cross["finish_position"] == 1
                        ).sum() / len(same_cross)
                        stats["cross_avg_finish"] = same_cross["finish_position"].mean()
                        stats["is_golden_cross"] = (
                            1
                            if stats["cross_win_rate"] > 0.2
                            and stats["cross_count"] > 10
                            else 0
                        )
                    else:
                        stats["cross_count"] = 0
                        stats["cross_win_rate"] = 0
                        stats["cross_avg_finish"] = np.nan
                        stats["is_golden_cross"] = 0

                    # 血統系統の特徴
                    stats["is_inbreed"] = self._check_inbreeding(
                        sire_id, dam_sire_id, row
                    )
                else:
                    stats = {
                        "cross_count": 0,
                        "cross_win_rate": 0,
                        "cross_avg_finish": np.nan,
                        "is_golden_cross": 0,
                        "is_inbreed": 0,
                    }

                affinity_stats.append(stats)

            # データフレームに結合
            if affinity_stats:
                affinity_df = pd.DataFrame(affinity_stats, index=df.index)
                df_features = pd.concat([df_features, affinity_df], axis=1)
                self.feature_names.extend(affinity_df.columns.tolist())
                self.feature_count += len(affinity_df.columns)

            logger.info("血統相性特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"血統相性特徴量抽出中にエラーが発生しました: {e!s}"
            ) from e

    def _get_distance_category(self, distance: float) -> str:
        """距離カテゴリの取得

        Args:
            distance: 距離

        Returns:
            カテゴリ名
        """
        if distance <= 1400:
            return "sprint"
        if distance <= 1800:
            return "mile"
        if distance <= 2200:
            return "intermediate"
        return "long"

    def _get_default_sire_stats(self) -> dict:
        """デフォルトの父馬統計

        Returns:
            デフォルト値の辞書
        """
        return {
            "sire_progeny_count": 0,
            "sire_win_count": 0,
            "sire_win_rate": 0,
            "sire_place_rate": 0,
            "sire_show_rate": 0,
            "sire_avg_finish": np.nan,
            "sire_earnings_avg": 0,
            "is_important_sire": 0,
        }

    def _get_default_dam_sire_stats(self) -> dict:
        """デフォルトの母父馬統計

        Returns:
            デフォルト値の辞書
        """
        return {
            "dam_sire_progeny_count": 0,
            "dam_sire_win_rate": 0,
            "dam_sire_avg_finish": np.nan,
            "dam_sire_stamina_index": 0,
            "dam_sire_speed_index": 0,
        }

    def _get_default_sibling_stats(self) -> dict:
        """デフォルトの兄弟馬統計

        Returns:
            デフォルト値の辞書
        """
        return {
            "sibling_count": 0,
            "sibling_race_count": 0,
            "sibling_win_count": 0,
            "sibling_win_rate": 0,
            "sibling_avg_finish": np.nan,
            "sibling_earnings_total": 0,
            "has_g1_winner_sibling": 0,
            "is_first_foal": 0,
        }

    def _check_inbreeding(self, sire_id: any, dam_sire_id: any, row: pd.Series) -> int:
        """インブリードのチェック(簡易版)

        Args:
            sire_id: 父馬ID
            dam_sire_id: 母父馬ID
            row: レースデータの行

        Returns:
            インブリードフラグ(0 or 1)
        """
        # 簡易的な実装:父系と母系で同じ祖先がいるかのチェック
        # 実際にはもっと詳細な血統表が必要

        # 重要種牡馬の系統チェック(仮実装)

        # 実装は簡略化
        return 0

    def extract_all_pedigree_features(
        self,
        df: pd.DataFrame,
        sire_performance: pd.DataFrame,
        dam_sire_performance: pd.DataFrame,
        sibling_performance: pd.DataFrame,
        horse_pedigree: pd.DataFrame,
        bloodline_cross_performance: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """全ての血統特徴量を抽出

        Args:
            df: 現在のレースデータ
            sire_performance: 父馬の産駒成績データ
            dam_sire_performance: 母父馬の産駒成績データ
            sibling_performance: 全馬の成績データ
            horse_pedigree: 馬の血統情報
            bloodline_cross_performance: 血統配合の成績データ

        Returns:
            全特徴量追加後のデータフレーム
        """
        logger.info("全血統特徴量抽出開始")

        try:
            # 父馬特徴量
            df_features = self.extract_sire_features(
                df, sire_performance, horse_pedigree
            )

            # 母父馬特徴量
            df_features = self.extract_dam_sire_features(
                df_features, dam_sire_performance, horse_pedigree
            )

            # 兄弟馬特徴量
            df_features = self.extract_sibling_features(
                df_features, sibling_performance, horse_pedigree
            )

            # 血統相性特徴量
            if bloodline_cross_performance is not None:
                df_features = self.extract_bloodline_affinity(
                    df_features, bloodline_cross_performance
                )

            logger.info(
                f"✅ 血統特徴量抽出完了: 合計{self.feature_count}個の特徴量を生成"
            )
            logger.info(f"生成された特徴量: {self.feature_names}")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"全血統特徴量抽出中にエラーが発生しました: {e!s}"
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
                "sire": "父馬成績特徴量",
                "dam_sire": "母父馬成績特徴量",
                "sibling": "兄弟馬成績特徴量",
                "affinity": "血統相性特徴量",
            },
        }
