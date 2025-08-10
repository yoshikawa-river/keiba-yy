"""Phase1残り特徴量（レース条件・血統）のテストコード

レース条件特徴量15個と血統基本特徴量15個のテストを実装。
"""

import unittest

import pandas as pd

from src.features.extractors.pedigree_basic import PedigreeBasicExtractor
from src.features.extractors.race_condition import RaceConditionExtractor


class TestRaceConditionExtractor(unittest.TestCase):
    """レース条件特徴量抽出器のテスト"""

    def setUp(self):
        """テストデータのセットアップ"""
        self.extractor = RaceConditionExtractor()

        # テスト用レースデータ
        self.df = pd.DataFrame(
            {
                "race_id": ["R001", "R002", "R003"],
                "horse_id": ["H001", "H002", "H003"],
                "distance": [1200, 1600, 2400],
                "race_class": ["G1", "2勝", "未勝利"],
                "field_size": [18, 12, 8],
                "venue": ["東京", "中山", "新潟"],
                "track_type": ["turf", "dirt", "turf"],
                "track_condition": ["good", "heavy", "yielding"],
            }
        )

    def test_extract_basic_race_features(self):
        """基本レース条件特徴量のテスト"""
        result = self.extractor.extract_basic_race_features(self.df)

        # 特徴量が追加されていることを確認
        self.assertIn("distance_category", result.columns)
        self.assertIn("distance_normalized", result.columns)
        self.assertIn("distance_squared", result.columns)
        self.assertIn("class_rank", result.columns)
        self.assertIn("is_graded_race", result.columns)
        self.assertIn("field_size_normalized", result.columns)
        self.assertIn("is_large_field", result.columns)
        self.assertIn("is_small_field", result.columns)

        # 値の範囲確認
        self.assertTrue((result["distance_normalized"] >= 0).all())
        self.assertTrue((result["distance_normalized"] <= 1).all())
        self.assertTrue((result["field_size_normalized"] >= 0).all())
        self.assertTrue((result["field_size_normalized"] <= 1).all())

        # カテゴリ値の確認
        self.assertTrue(result["distance_category"].iloc[0] == 0)  # 1200m = sprint
        self.assertTrue(result["distance_category"].iloc[1] == 1)  # 1600m = mile
        self.assertTrue(result["distance_category"].iloc[2] == 3)  # 2400m = long

        # 特徴量数の確認
        self.assertEqual(self.extractor.feature_count, 8)

    def test_extract_track_features(self):
        """競馬場・コース特徴量のテスト"""
        result = self.extractor.extract_track_features(self.df)

        # 特徴量が追加されていることを確認
        self.assertIn("venue_encoded", result.columns)
        self.assertIn("is_left_turn", result.columns)
        self.assertIn("is_large_track", result.columns)
        self.assertIn("is_local_track", result.columns)
        self.assertIn("is_turf", result.columns)
        self.assertIn("is_dirt", result.columns)
        self.assertIn("track_condition_encoded", result.columns)

        # 値の確認
        self.assertEqual(result["venue_encoded"].iloc[0], 1)  # 東京
        self.assertEqual(result["is_left_turn"].iloc[0], 1)  # 東京は左回り
        self.assertEqual(result["is_large_track"].iloc[0], 1)  # 東京は大規模
        self.assertEqual(result["is_turf"].iloc[0], 1)  # 芝
        self.assertEqual(result["is_dirt"].iloc[1], 1)  # ダート

        # 特徴量数の確認
        self.assertEqual(self.extractor.feature_count, 7)

    def test_extract_all_race_condition_features(self):
        """全レース条件特徴量の統合テスト"""
        self.extractor.extract_all_race_condition_features(self.df)

        # 全15個の特徴量が生成されることを確認
        self.assertEqual(self.extractor.feature_count, 15)
        self.assertEqual(len(self.extractor.feature_names), 15)

        # 各カテゴリの特徴量数を確認
        info = self.extractor.get_feature_info()
        self.assertEqual(info["categories"]["basic_race"], 8)
        self.assertEqual(info["categories"]["track"], 7)

        print(f"✅ レース条件特徴量テスト完了: {self.extractor.feature_count}個の特徴量を確認")


class TestPedigreeBasicExtractor(unittest.TestCase):
    """血統基本特徴量抽出器のテスト"""

    def setUp(self):
        """テストデータのセットアップ"""
        self.extractor = PedigreeBasicExtractor()

        # テスト用レースデータ
        self.df = pd.DataFrame(
            {
                "race_id": ["R001", "R002", "R003"],
                "horse_id": ["H001", "H002", "H003"],
                "distance": [1600, 2000, 1200],
            }
        )

        # テスト用血統データ
        self.pedigree_df = pd.DataFrame(
            {
                "horse_id": ["H001", "H002", "H003"],
                "sire_id": ["S001", "S002", "S003"],
                "sire_name": ["Deep Impact", "King Kamehameha", "Lord Kanaloa"],
                "sire_win_rate": [0.25, 0.20, 0.22],
                "sire_place_rate": [0.55, 0.48, 0.50],
                "sire_avg_earnings": [10000000, 8000000, 9000000],
                "dam_sire_id": ["DS001", "DS002", "DS003"],
                "dam_sire_name": ["Sunday Silence", "Storm Cat", "Mr. Prospector"],
                "dam_sire_win_rate": [0.23, 0.18, 0.20],
                "dam_sire_place_rate": [0.52, 0.45, 0.47],
                "dam_progeny_count": [5, 3, 7],
                "has_inbreeding": [False, True, False],
                "is_imported_sire": [False, False, True],
            }
        )

    def test_extract_sire_features(self):
        """父系特徴量のテスト"""
        result = self.extractor.extract_sire_features(self.df, self.pedigree_df)

        # 特徴量が追加されていることを確認
        self.assertIn("sire_encoded", result.columns)
        self.assertIn("sire_bloodline", result.columns)
        self.assertIn("sire_win_rate", result.columns)
        self.assertIn("sire_place_rate", result.columns)
        self.assertIn("sire_earnings_log", result.columns)

        # 値の確認
        self.assertTrue((result["sire_win_rate"] >= 0).all())
        self.assertTrue((result["sire_win_rate"] <= 1).all())
        self.assertTrue((result["sire_place_rate"] >= 0).all())
        self.assertTrue((result["sire_place_rate"] <= 1).all())

        # 特徴量数の確認
        self.assertEqual(self.extractor.feature_count, 5)

    def test_extract_dam_sire_features(self):
        """母父系特徴量のテスト"""
        result = self.extractor.extract_dam_sire_features(self.df, self.pedigree_df)

        # 特徴量が追加されていることを確認
        self.assertIn("dam_sire_encoded", result.columns)
        self.assertIn("dam_sire_bloodline", result.columns)
        self.assertIn("dam_sire_win_rate", result.columns)
        self.assertIn("dam_sire_place_rate", result.columns)
        self.assertIn("dam_vitality", result.columns)

        # 値の確認
        self.assertTrue((result["dam_sire_win_rate"] >= 0).all())
        self.assertTrue((result["dam_sire_win_rate"] <= 1).all())
        self.assertTrue((result["dam_vitality"] >= 0).all())
        self.assertTrue((result["dam_vitality"] <= 1).all())

        # 特徴量数の確認
        self.assertEqual(self.extractor.feature_count, 5)

    def test_extract_bloodline_compatibility_features(self):
        """血統相性・距離適性特徴量のテスト"""
        result = self.extractor.extract_bloodline_compatibility_features(
            self.df, self.pedigree_df
        )

        # 特徴量が追加されていることを確認
        self.assertIn("nick_score", result.columns)
        self.assertIn("distance_aptitude_score", result.columns)
        self.assertIn("inbreeding_flag", result.columns)
        self.assertIn("bloodline_match_score", result.columns)
        self.assertIn("is_imported_bloodline", result.columns)

        # 値の確認
        self.assertTrue((result["nick_score"] >= 0).all())
        self.assertTrue((result["nick_score"] <= 1).all())
        self.assertTrue((result["distance_aptitude_score"] >= 0).all())
        self.assertTrue((result["distance_aptitude_score"] <= 1).all())

        # 特徴量数の確認
        self.assertEqual(self.extractor.feature_count, 5)

    def test_extract_all_pedigree_features(self):
        """全血統基本特徴量の統合テスト"""
        self.extractor.extract_all_pedigree_features(
            self.df, self.pedigree_df
        )

        # 全15個の特徴量が生成されることを確認
        self.assertEqual(self.extractor.feature_count, 15)
        self.assertEqual(len(self.extractor.feature_names), 15)

        # 各カテゴリの特徴量数を確認
        info = self.extractor.get_feature_info()
        self.assertEqual(info["categories"]["sire"], 5)
        self.assertEqual(info["categories"]["dam_sire"], 5)
        self.assertEqual(info["categories"]["compatibility"], 5)

        print(f"✅ 血統基本特徴量テスト完了: {self.extractor.feature_count}個の特徴量を確認")


class TestFeatureCompleteness(unittest.TestCase):
    """Phase1特徴量の完全性テスト"""

    def test_phase1_feature_count(self):
        """Phase1の全100個の特徴量が実装されていることを確認"""
        # 各抽出器のインスタンス化
        from src.features.extractors.horse_performance import HorsePerformanceExtractor
        from src.features.extractors.jockey_trainer import JockeyTrainerFeatureExtractor
        from src.features.extractors.time_features import TimeFeatureExtractor

        perf_extractor = HorsePerformanceExtractor()
        time_extractor = TimeFeatureExtractor()
        jt_extractor = JockeyTrainerFeatureExtractor()
        race_extractor = RaceConditionExtractor()
        pedigree_extractor = PedigreeBasicExtractor()

        # テストデータ作成
        df = pd.DataFrame(
            {
                "race_id": ["R001"],
                "horse_id": ["H001"],
                "jockey_id": ["J001"],
                "trainer_id": ["T001"],
                "distance": [1600],
                "track_type": ["turf"],
                "race_class": ["G1"],
                "field_size": [18],
                "venue": ["東京"],
                "track_condition": ["good"],
            }
        )

        # 各特徴量抽出
        df = perf_extractor.extract_all_performance_features(df)
        df = time_extractor.extract_all_time_features(df)
        df = jt_extractor.extract_all_jockey_trainer_features(df)
        df = race_extractor.extract_all_race_condition_features(df)
        df = pedigree_extractor.extract_all_pedigree_features(df)

        # 合計100個の特徴量が生成されることを確認
        total_features = (
            perf_extractor.feature_count
            + time_extractor.feature_count
            + jt_extractor.feature_count
            + race_extractor.feature_count
            + pedigree_extractor.feature_count
        )

        self.assertEqual(total_features, 100)

        # 内訳の確認
        print("\n📊 Phase1特徴量の内訳:")
        print(f"  - 馬の成績特徴量: {perf_extractor.feature_count}個")
        print(f"  - タイム特徴量: {time_extractor.feature_count}個")
        print(f"  - 騎手・調教師特徴量: {jt_extractor.feature_count}個")
        print(f"  - レース条件特徴量: {race_extractor.feature_count}個")
        print(f"  - 血統基本特徴量: {pedigree_extractor.feature_count}個")
        print(f"  合計: {total_features}個")
        print("\n✅ Phase1特徴量100個全て実装完了！")


if __name__ == "__main__":
    unittest.main()

