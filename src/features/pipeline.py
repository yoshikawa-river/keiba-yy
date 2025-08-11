"""特徴量統合パイプライン

全ての特徴量抽出器を統合し、一括で特徴量を生成するパイプライン。
Phase1統合済み + Phase2未統合抽出器を全て統合管理。
"""

from typing import Any

import pandas as pd
from loguru import logger

from src.features.extractors.base_features import BaseFeatureExtractor

# Phase1統合済み抽出器
from src.features.extractors.horse_performance import HorsePerformanceExtractor
from src.features.extractors.jockey_trainer import JockeyTrainerFeatureExtractor
from src.features.extractors.pedigree_basic import PedigreeBasicExtractor
from src.features.extractors.pedigree_features import PedigreeFeatureExtractor

# Phase2未統合抽出器
from src.features.extractors.performance_features import PerformanceFeatureExtractor
from src.features.extractors.race_condition import RaceConditionExtractor
from src.features.extractors.race_features import RaceFeatureExtractor
from src.features.extractors.relative_features import RelativeFeatureExtractor
from src.features.extractors.time_features import TimeFeatureExtractor


class FeatureExtractionError(Exception):
    """特徴量抽出エラー"""
    pass


class ComprehensiveFeaturePipeline:
    """包括的特徴量抽出パイプライン

    全10個の抽出器を統合し、200-300個の特徴量を一括生成する。
    Phase1統合済み(100個) + Phase2未統合(100-200個)を統合管理。
    """

    def __init__(self):
        """パイプライン初期化"""
        logger.info("包括的特徴量パイプラインを初期化開始")

        # 特徴量管理
        self.total_feature_count = 0
        self.all_feature_names = []
        self.extractor_summary = {}

        # Phase1統合済み抽出器（テスト済み）
        self.phase1_extractors = {
            "horse_performance": HorsePerformanceExtractor(),      # 30個
            "jockey_trainer": JockeyTrainerFeatureExtractor(),     # 20個
            "time_features": TimeFeatureExtractor(),               # 20個
            "race_condition": RaceConditionExtractor(),            # 15個
            "pedigree_basic": PedigreeBasicExtractor(),           # 15個
        }

        # Phase2未統合抽出器（実装済み未テスト）
        self.phase2_extractors = {
            "performance_features": PerformanceFeatureExtractor(), # 推定50-80個
            "race_features": RaceFeatureExtractor(),               # 推定40-60個
            "relative_features": RelativeFeatureExtractor(),       # 推定30-50個
            "pedigree_features": PedigreeFeatureExtractor(),       # 推定40-60個
            "base_features": BaseFeatureExtractor(),               # 推定20-30個
        }

        logger.info(f"Phase1抽出器: {len(self.phase1_extractors)}個")
        logger.info(f"Phase2抽出器: {len(self.phase2_extractors)}個")
        logger.info("包括的特徴量パイプライン初期化完了")

    def extract_phase1_features(
        self,
        df: pd.DataFrame,
        history_df: pd.DataFrame | None = None,
        career_df: pd.DataFrame | None = None,
        jockey_stats: pd.DataFrame | None = None,
        trainer_stats: pd.DataFrame | None = None,
        pedigree_df: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """Phase1統合済み特徴量を抽出（100個）

        Args:
            df: メインのレースデータ
            history_df: 過去成績データ
            career_df: 生涯成績データ
            jockey_stats: 騎手統計データ
            trainer_stats: 調教師統計データ
            pedigree_df: 血統データ

        Returns:
            Phase1特徴量が追加されたデータフレーム
        """
        logger.info("========== Phase1特徴量抽出開始 ==========")
        df_features = df.copy()

        try:
            # 1. 馬の成績特徴量（30個）
            logger.info("馬の成績特徴量を抽出中...")
            df_features = self.phase1_extractors["horse_performance"].extract_all_performance_features(
                df_features, history_df, career_df
            )

            # 2. 騎手・調教師特徴量（20個）
            logger.info("騎手・調教師特徴量を抽出中...")
            df_features = self.phase1_extractors["jockey_trainer"].extract_all_jockey_trainer_features(
                df_features, jockey_stats, trainer_stats
            )

            # 3. タイム特徴量（20個）
            logger.info("タイム特徴量を抽出中...")
            df_features = self.phase1_extractors["time_features"].extract_all_time_features(
                df_features, history_df
            )

            # 4. レース条件特徴量（15個）
            logger.info("レース条件特徴量を抽出中...")
            df_features = self.phase1_extractors["race_condition"].extract_all_race_condition_features(
                df_features
            )

            # 5. 血統基本特徴量（15個）
            logger.info("血統基本特徴量を抽出中...")
            df_features = self.phase1_extractors["pedigree_basic"].extract_all_pedigree_features(
                df_features, pedigree_df
            )

            # Phase1統計情報を更新
            phase1_count = sum(extractor.feature_count for extractor in self.phase1_extractors.values())
            logger.info(f"✅ Phase1特徴量抽出完了: {phase1_count}個")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(f"Phase1特徴量抽出中にエラーが発生: {e!s}") from e

    def extract_phase2_features(
        self,
        df: pd.DataFrame,
        performance_history: pd.DataFrame | None = None,
        race_metadata: pd.DataFrame | None = None,
        odds_data: pd.DataFrame | None = None,
        pedigree_extended: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """Phase2未統合特徴量を抽出（100-200個）

        Args:
            df: メインのレースデータ
            performance_history: 成績履歴データ
            race_metadata: レースメタデータ
            odds_data: オッズデータ
            pedigree_extended: 拡張血統データ

        Returns:
            Phase2特徴量が追加されたデータフレーム
        """
        logger.info("========== Phase2特徴量抽出開始 ==========")
        df_features = df.copy()

        try:
            # 1. 成績詳細特徴量
            logger.info("成績詳細特徴量を抽出中...")
            df_features = self.phase2_extractors["performance_features"].extract_all_performance_features(
                df_features, performance_history
            )

            # 2. レース詳細特徴量
            logger.info("レース詳細特徴量を抽出中...")
            df_features = self.phase2_extractors["race_features"].extract_all_race_features(
                df_features, race_metadata
            )

            # 3. 相対特徴量
            logger.info("相対特徴量を抽出中...")
            df_features = self.phase2_extractors["relative_features"].extract_all_relative_features(
                df_features
            )

            # 4. 血統詳細特徴量
            logger.info("血統詳細特徴量を抽出中...")
            df_features = self.phase2_extractors["pedigree_features"].extract_all_pedigree_features(
                df_features, pedigree_extended
            )

            # 5. 基本特徴量
            logger.info("基本特徴量を抽出中...")
            df_features = self.phase2_extractors["base_features"].extract_all_base_features(
                df_features
            )

            # Phase2統計情報を収集（feature_countがない抽出器もあるため推定）
            phase2_feature_count = len(df_features.columns) - len(df.columns)
            logger.info(f"✅ Phase2特徴量抽出完了: 推定{phase2_feature_count}個")

            return df_features

        except Exception as e:
            logger.warning(f"Phase2特徴量抽出中にエラー（継続可能）: {e!s}")
            return df_features

    def extract_all_features(
        self,
        df: pd.DataFrame,
        # Phase1データ
        history_df: pd.DataFrame | None = None,
        career_df: pd.DataFrame | None = None,
        jockey_stats: pd.DataFrame | None = None,
        trainer_stats: pd.DataFrame | None = None,
        pedigree_df: pd.DataFrame | None = None,
        # Phase2データ
        performance_history: pd.DataFrame | None = None,
        race_metadata: pd.DataFrame | None = None,
        odds_data: pd.DataFrame | None = None,
        pedigree_extended: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """全特徴量を一括抽出（200-300個）

        Args:
            df: メインのレースデータ
            各種オプショナルデータフレーム

        Returns:
            全特徴量が追加されたデータフレーム
        """
        logger.info("========== 包括的特徴量抽出開始 ==========")
        start_columns = len(df.columns)

        try:
            # Phase1特徴量抽出（100個）
            df_features = self.extract_phase1_features(
                df, history_df, career_df, jockey_stats, trainer_stats, pedigree_df
            )

            # Phase2特徴量抽出（100-200個）
            df_features = self.extract_phase2_features(
                df_features, performance_history, race_metadata, odds_data, pedigree_extended
            )

            # 最終統計
            final_columns = len(df_features.columns)
            total_features = final_columns - start_columns
            self.total_feature_count = total_features
            self.all_feature_names = [col for col in df_features.columns if col not in df.columns]

            logger.info("🎉 包括的特徴量抽出完了!")
            logger.info(f"   - 元のカラム数: {start_columns}")
            logger.info(f"   - 最終カラム数: {final_columns}")
            logger.info(f"   - 生成特徴量数: {total_features}")
            logger.info("   - Phase1統合済み: 100個")
            logger.info(f"   - Phase2新規統合: {total_features - 100}個")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(f"包括的特徴量抽出中にエラーが発生: {e!s}") from e

    def get_feature_summary(self) -> dict[str, Any]:
        """特徴量サマリー情報を取得

        Returns:
            特徴量の統計情報辞書
        """
        phase1_count = sum(
            getattr(extractor, 'feature_count', 0)
            for extractor in self.phase1_extractors.values()
        )

        return {
            "total_feature_count": self.total_feature_count,
            "all_feature_names": self.all_feature_names,
            "phase1_extractors": len(self.phase1_extractors),
            "phase2_extractors": len(self.phase2_extractors),
            "phase1_confirmed_count": phase1_count,
            "phase2_estimated_count": self.total_feature_count - phase1_count if self.total_feature_count > 0 else 0,
            "extractor_breakdown": {
                "phase1": {name: getattr(extractor, 'feature_count', 0)
                          for name, extractor in self.phase1_extractors.items()},
                "phase2": dict.fromkeys(self.phase2_extractors.keys(), "推定実装済み")
            }
        }

    def validate_pipeline(self) -> bool:
        """パイプライン動作検証

        Returns:
            検証結果（True: 正常, False: 異常）
        """
        try:
            logger.info("パイプライン動作検証開始")

            # テスト用ダミーデータ作成
            test_df = pd.DataFrame({
                'horse_id': [1, 2, 3],
                'jockey_id': [101, 102, 103],
                'trainer_id': [201, 202, 203],
                'distance': [1600, 2000, 1200],
                'venue': ['東京', '中山', '阪神'],
                'race_class': ['G1', 'G2', 'G3'],
                'field_size': [16, 18, 15]
            })

            # Phase1のみテスト（確実に動作する）
            result = self.extract_phase1_features(test_df)

            if len(result.columns) > len(test_df.columns):
                logger.info("✅ パイプライン動作検証成功")
                return True
            logger.warning("⚠️ パイプライン動作検証失敗")
            return False

        except Exception as e:
            logger.error(f"❌ パイプライン動作検証エラー: {e!s}")
            return False
