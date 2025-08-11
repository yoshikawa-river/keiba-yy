"""統合バリデーションテスト

全抽出器のfeature_count管理が正しく実装されているかを確認
"""

import sys

sys.path.append("src")


def test_extractor_feature_count_management():
    """全抽出器のfeature_count管理をテスト"""
    print("=== 抽出器統合バリデーションテスト ===\n")

    # Phase1抽出器（既存）
    print("Phase1抽出器（統合済み）:")
    try:
        from src.features.extractors.horse_performance import HorsePerformanceExtractor

        extractor = HorsePerformanceExtractor()
        print(f"✅ HorsePerformanceExtractor: feature_count = {extractor.feature_count}")
    except Exception as e:
        print(f"❌ HorsePerformanceExtractor: {e}")

    try:
        from src.features.extractors.jockey_trainer import JockeyTrainerFeatureExtractor

        extractor = JockeyTrainerFeatureExtractor()
        print(
            f"✅ JockeyTrainerFeatureExtractor: feature_count = {extractor.feature_count}"
        )
    except Exception as e:
        print(f"❌ JockeyTrainerFeatureExtractor: {e}")

    try:
        from src.features.extractors.time_features import TimeFeatureExtractor

        extractor = TimeFeatureExtractor()
        print(f"✅ TimeFeatureExtractor: feature_count = {extractor.feature_count}")
    except Exception as e:
        print(f"❌ TimeFeatureExtractor: {e}")

    try:
        from src.features.extractors.race_condition import RaceConditionExtractor

        extractor = RaceConditionExtractor()
        print(f"✅ RaceConditionExtractor: feature_count = {extractor.feature_count}")
    except Exception as e:
        print(f"❌ RaceConditionExtractor: {e}")

    try:
        from src.features.extractors.pedigree_basic import PedigreeBasicExtractor

        extractor = PedigreeBasicExtractor()
        print(f"✅ PedigreeBasicExtractor: feature_count = {extractor.feature_count}")
    except Exception as e:
        print(f"❌ PedigreeBasicExtractor: {e}")

    print("\nPhase2抽出器（新規統合）:")
    # Phase2抽出器（新規統合）
    try:
        from src.features.extractors.performance_features import (
            PerformanceFeatureExtractor,
        )

        extractor = PerformanceFeatureExtractor()
        print(
            f"✅ PerformanceFeatureExtractor: feature_count = {extractor.feature_count}"
        )
        print(
            f"   - get_feature_summary method: {'✅' if hasattr(extractor, 'get_feature_summary') else '❌'}"
        )
    except Exception as e:
        print(f"❌ PerformanceFeatureExtractor: {e}")

    try:
        from src.features.extractors.relative_features import RelativeFeatureExtractor

        extractor = RelativeFeatureExtractor()
        print(f"✅ RelativeFeatureExtractor: feature_count = {extractor.feature_count}")
        print(
            f"   - get_feature_summary method: {'✅' if hasattr(extractor, 'get_feature_summary') else '❌'}"
        )
    except Exception as e:
        print(f"❌ RelativeFeatureExtractor: {e}")

    try:
        from src.features.extractors.pedigree_features import PedigreeFeatureExtractor

        extractor = PedigreeFeatureExtractor()
        print(f"✅ PedigreeFeatureExtractor: feature_count = {extractor.feature_count}")
        print(
            f"   - get_feature_summary method: {'✅' if hasattr(extractor, 'get_feature_summary') else '❌'}"
        )
    except Exception as e:
        print(f"❌ PedigreeFeatureExtractor: {e}")

    try:
        from src.features.extractors.race_features import RaceFeatureExtractor

        extractor = RaceFeatureExtractor()
        print(
            f"✅ RaceFeatureExtractor: feature_count = {getattr(extractor, 'feature_count', 'N/A')}"
        )
        print(
            f"   - get_feature_summary method: {'✅' if hasattr(extractor, 'get_feature_summary') else '❌'}"
        )
    except Exception as e:
        print(f"❌ RaceFeatureExtractor: {e}")

    try:
        from src.features.extractors.base_features import BaseFeatureExtractor

        extractor = BaseFeatureExtractor()
        print(f"✅ BaseFeatureExtractor: feature_count = {extractor.feature_count}")
        print(
            f"   - get_feature_types method: {'✅' if hasattr(extractor, 'get_feature_types') else '❌'}"
        )
    except Exception as e:
        print(f"❌ BaseFeatureExtractor: {e}")

    # 統合パイプラインテスト
    print("\n統合パイプライン:")
    try:
        from src.features.pipeline import ComprehensiveFeaturePipeline

        pipeline = ComprehensiveFeaturePipeline()
        print("✅ ComprehensiveFeaturePipeline: 初期化成功")
        print(f"   - Phase1抽出器: {len(pipeline.phase1_extractors)}個")
        print(f"   - Phase2抽出器: {len(pipeline.phase2_extractors)}個")

        # サマリー取得テスト
        summary = pipeline.get_feature_summary()
        print(
            f"   - get_feature_summary: ✅ (total_count: {summary['total_feature_count']})"
        )

        # バリデーションテスト
        validation_result = pipeline.validate_pipeline()
        print(f"   - validate_pipeline: {'✅' if validation_result else '❌'}")

    except Exception as e:
        print(f"❌ ComprehensiveFeaturePipeline: {e}")

    print("\n=== バリデーション完了 ===")


if __name__ == "__main__":
    test_extractor_feature_count_management()
