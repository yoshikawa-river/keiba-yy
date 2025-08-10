"""Phase1特徴量抽出器のユニットテスト

基本成績、タイム、騎手・調教師特徴量のテストを実装。
"""

import unittest
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src.features.extractors.horse_performance import HorsePerformanceExtractor
from src.features.extractors.jockey_trainer import JockeyTrainerFeatureExtractor
from src.features.extractors.time_features import TimeFeatureExtractor


class TestHorsePerformanceExtractor(unittest.TestCase):
    """馬の成績特徴量抽出器のテスト"""

    def setUp(self):
        """テストデータのセットアップ"""
        self.extractor = HorsePerformanceExtractor()
        
        # テスト用レースデータ
        self.df = pd.DataFrame({
            "race_id": ["R001", "R001", "R001"],
            "horse_id": ["H001", "H002", "H003"],
            "distance": [1600, 1600, 1600],
            "track_type": ["turf", "turf", "turf"],
            "track_condition": ["good", "good", "good"],
            "venue": ["東京", "東京", "東京"],
            "race_class": ["G1", "G1", "G1"],
            "race_date": ["2024-01-01", "2024-01-01", "2024-01-01"],
            "post_position": [1, 5, 10],
            "weight_carried": [55, 56, 57]
        })
        
        # テスト用過去成績データ
        self.history_df = pd.DataFrame({
            "horse_id": ["H001"] * 10 + ["H002"] * 10 + ["H003"] * 10,
            "race_date": pd.date_range("2023-01-01", periods=10).tolist() * 3,
            "finish_position": [1, 2, 3, 1, 5, 2, 3, 4, 1, 2] * 3,
            "distance": [1600] * 30,
            "track_condition": ["good"] * 30,
            "venue": ["東京"] * 30,
            "race_class": ["G1"] * 30,
            "post_position": list(range(1, 11)) * 3,
            "weight_carried": [55] * 30,
            "prize_money": [10000000] * 30,
            "race_grade": ["G1"] * 15 + ["G2"] * 15
        })

    def test_extract_past_performance_stats(self):
        """過去成績統計特徴量の抽出テスト"""
        result = self.extractor.extract_past_performance_stats(
            self.df, self.history_df
        )
        
        # 特徴量が追加されていることを確認
        self.assertIn("avg_finish_position_last3", result.columns)
        self.assertIn("median_finish_position_last5", result.columns)
        self.assertIn("std_finish_position_last3", result.columns)
        self.assertIn("best_finish_last5", result.columns)
        self.assertIn("worst_finish_last5", result.columns)
        self.assertIn("win_count_last10", result.columns)
        self.assertIn("consistency_score", result.columns)
        self.assertIn("recent_form_trend", result.columns)
        
        # 値が数値であることを確認
        self.assertTrue(pd.api.types.is_numeric_dtype(result["avg_finish_position_last3"]))
        
        # 特徴量数の確認
        self.assertEqual(self.extractor.feature_count, 15)

    def test_extract_career_performance(self):
        """生涯成績特徴量の抽出テスト"""
        result = self.extractor.extract_career_performance(
            self.df, self.history_df
        )
        
        # 特徴量が追加されていることを確認
        self.assertIn("career_win_rate", result.columns)
        self.assertIn("career_place_rate", result.columns)
        self.assertIn("career_show_rate", result.columns)
        self.assertIn("career_starts", result.columns)
        self.assertIn("career_earnings", result.columns)
        self.assertIn("career_g1_wins", result.columns)
        
        # 勝率が0-1の範囲内であることを確認
        self.assertTrue((result["career_win_rate"] >= 0).all())
        self.assertTrue((result["career_win_rate"] <= 1).all())
        
        # 特徴量数の確認
        self.assertEqual(self.extractor.feature_count, 8)

    def test_extract_conditional_performance(self):
        """条件別成績特徴量の抽出テスト"""
        result = self.extractor.extract_conditional_performance(
            self.df, self.history_df
        )
        
        # 特徴量が追加されていることを確認
        self.assertIn("distance_category_win_rate", result.columns)
        self.assertIn("track_condition_win_rate", result.columns)
        self.assertIn("venue_win_rate", result.columns)
        self.assertIn("class_win_rate", result.columns)
        self.assertIn("position_win_rate", result.columns)
        
        # 特徴量数の確認
        self.assertEqual(self.extractor.feature_count, 7)

    def test_extract_all_performance_features(self):
        """全成績特徴量の統合テスト"""
        result = self.extractor.extract_all_performance_features(
            self.df, self.history_df, self.history_df
        )
        
        # 全30個の特徴量が生成されることを確認
        self.assertEqual(self.extractor.feature_count, 30)
        self.assertEqual(len(self.extractor.feature_names), 30)
        
        # NaN値がないことを確認（デフォルト値0で埋められている）
        for feat in self.extractor.feature_names:
            self.assertFalse(result[feat].isna().any())


class TestTimeFeatureExtractor(unittest.TestCase):
    """タイム特徴量抽出器のテスト"""

    def setUp(self):
        """テストデータのセットアップ"""
        self.extractor = TimeFeatureExtractor()
        
        # テスト用レースデータ
        self.df = pd.DataFrame({
            "race_id": ["R001", "R001", "R001"],
            "horse_id": ["H001", "H002", "H003"],
            "distance": [1600, 1600, 1600],
            "track_type": ["turf", "turf", "turf"],
            "track_condition": ["good", "good", "good"]
        })
        
        # テスト用過去成績データ（タイム情報含む）
        self.history_df = pd.DataFrame({
            "horse_id": ["H001"] * 5 + ["H002"] * 5 + ["H003"] * 5,
            "race_id": ["R" + str(i) for i in range(15)],
            "race_date": pd.date_range("2023-01-01", periods=5).tolist() * 3,
            "race_time": ["1:33.5", "1:34.0", "1:33.8", "1:34.2", "1:33.6"] * 3,
            "last_3f": [33.5, 34.0, 33.8, 34.2, 33.6] * 3,
            "last_3f_rank": [1, 3, 2, 4, 1] * 3,
            "distance": [1600] * 15,
            "track_type": ["turf"] * 15,
            "track_condition": ["good"] * 15
        })

    def test_time_to_seconds_conversion(self):
        """タイム文字列の秒変換テスト"""
        # 正常なケース
        self.assertEqual(self.extractor._time_to_seconds("1:33.5"), 93.5)
        self.assertEqual(self.extractor._time_to_seconds("2:01.2"), 121.2)
        
        # エッジケース
        self.assertEqual(self.extractor._time_to_seconds(""), 0)
        self.assertEqual(self.extractor._time_to_seconds(None), 0)

    def test_extract_race_time_features(self):
        """走破タイム特徴量の抽出テスト"""
        result = self.extractor.extract_race_time_features(
            self.df, self.history_df
        )
        
        # 特徴量が追加されていることを確認
        self.assertIn("last_race_time", result.columns)
        self.assertIn("avg_time_last3", result.columns)
        self.assertIn("avg_time_last5", result.columns)
        self.assertIn("best_time_at_distance", result.columns)
        self.assertIn("time_index", result.columns)
        self.assertIn("speed_figure", result.columns)
        
        # 特徴量数の確認
        self.assertEqual(self.extractor.feature_count, 10)

    def test_extract_last3f_features(self):
        """上がり3F特徴量の抽出テスト"""
        result = self.extractor.extract_last3f_features(
            self.df, self.history_df
        )
        
        # 特徴量が追加されていることを確認
        self.assertIn("last_3f_time", result.columns)
        self.assertIn("avg_last3f_last3", result.columns)
        self.assertIn("best_last3f", result.columns)
        self.assertIn("last3f_rank", result.columns)
        self.assertIn("last3f_consistency", result.columns)
        
        # 特徴量数の確認
        self.assertEqual(self.extractor.feature_count, 10)

    def test_get_base_time(self):
        """基準タイム取得のテスト"""
        # 芝1600m
        base_time = self.extractor._get_base_time(1600, "turf")
        self.assertEqual(base_time, 94.0)
        
        # ダート1800m
        base_time = self.extractor._get_base_time(1800, "dirt")
        self.assertEqual(base_time, 110.0)
        
        # 中間距離の補間
        base_time = self.extractor._get_base_time(1700, "turf")
        self.assertTrue(94.0 < base_time < 107.0)


class TestJockeyTrainerFeatureExtractor(unittest.TestCase):
    """騎手・調教師特徴量抽出器のテスト"""

    def setUp(self):
        """テストデータのセットアップ"""
        self.extractor = JockeyTrainerFeatureExtractor()
        
        # テスト用レースデータ
        self.df = pd.DataFrame({
            "race_id": ["R001", "R001", "R001"],
            "horse_id": ["H001", "H002", "H003"],
            "jockey_id": ["J001", "J002", "J003"],
            "trainer_id": ["T001", "T002", "T003"],
            "distance": [1600, 1600, 1600],
            "venue": ["東京", "東京", "東京"],
            "race_class": ["G1", "G1", "G1"]
        })
        
        # テスト用騎手統計データ
        self.jockey_stats = pd.DataFrame({
            "jockey_id": ["J001"] * 20 + ["J002"] * 20 + ["J003"] * 20,
            "race_date": pd.date_range("2023-01-01", periods=20).tolist() * 3,
            "finish_position": ([1, 2, 3, 4, 5] * 4) * 3,
            "distance": [1600] * 60,
            "venue": ["東京"] * 60,
            "race_class": ["G1"] * 60,
            "horse_id": ["H" + str(i % 10) for i in range(60)],
            "prize_money": [1000000] * 60
        })
        
        # テスト用調教師統計データ
        self.trainer_stats = pd.DataFrame({
            "trainer_id": ["T001"] * 20 + ["T002"] * 20 + ["T003"] * 20,
            "race_date": pd.date_range("2023-01-01", periods=20).tolist() * 3,
            "finish_position": ([1, 2, 3, 4, 5] * 4) * 3,
            "distance": [1600] * 60,
            "venue": ["東京"] * 60,
            "race_class": ["G1"] * 60,
            "jockey_id": ["J" + str(i % 10) for i in range(60)],
            "horse_id": ["H" + str(i % 10) for i in range(60)],
            "race_grade": ["G1"] * 30 + ["G2"] * 30
        })

    def test_extract_jockey_features(self):
        """騎手特徴量の抽出テスト"""
        result = self.extractor.extract_jockey_features(
            self.df, self.jockey_stats
        )
        
        # 特徴量が追加されていることを確認
        self.assertIn("jockey_win_rate", result.columns)
        self.assertIn("jockey_place_rate", result.columns)
        self.assertIn("jockey_show_rate", result.columns)
        self.assertIn("jockey_venue_win_rate", result.columns)
        self.assertIn("jockey_distance_win_rate", result.columns)
        self.assertIn("jockey_experience_years", result.columns)
        
        # 勝率が0-1の範囲内であることを確認
        self.assertTrue((result["jockey_win_rate"] >= 0).all())
        self.assertTrue((result["jockey_win_rate"] <= 1).all())
        
        # 特徴量数の確認
        self.assertEqual(self.extractor.feature_count, 10)

    def test_extract_trainer_features(self):
        """調教師特徴量の抽出テスト"""
        result = self.extractor.extract_trainer_features(
            self.df, self.trainer_stats
        )
        
        # 特徴量が追加されていることを確認
        self.assertIn("trainer_win_rate", result.columns)
        self.assertIn("trainer_place_rate", result.columns)
        self.assertIn("trainer_venue_win_rate", result.columns)
        self.assertIn("trainer_stable_size", result.columns)
        self.assertIn("trainer_g1_wins", result.columns)
        
        # 特徴量数の確認
        self.assertEqual(self.extractor.feature_count, 10)

    def test_get_distance_category(self):
        """距離カテゴリ分類のテスト"""
        self.assertEqual(self.extractor._get_distance_category(1200), "sprint")
        self.assertEqual(self.extractor._get_distance_category(1600), "mile")
        self.assertEqual(self.extractor._get_distance_category(2000), "intermediate")
        self.assertEqual(self.extractor._get_distance_category(2400), "long")

    def test_calculate_compatibility_score(self):
        """相性スコア計算のテスト"""
        positions = pd.Series([1, 2, 3, 4, 5])
        score = self.extractor._calculate_compatibility_score(positions)
        
        # スコアが0-1の範囲内であることを確認
        self.assertTrue(0 <= score <= 1)
        
        # 良い成績ほど高スコア
        good_positions = pd.Series([1, 1, 2])
        bad_positions = pd.Series([10, 12, 15])
        self.assertGreater(
            self.extractor._calculate_compatibility_score(good_positions),
            self.extractor._calculate_compatibility_score(bad_positions)
        )


class TestFeatureIntegration(unittest.TestCase):
    """特徴量抽出の統合テスト"""

    def test_all_phase1_features(self):
        """Phase1全特徴量（70個）の統合テスト"""
        # 各抽出器のインスタンス化
        perf_extractor = HorsePerformanceExtractor()
        time_extractor = TimeFeatureExtractor()
        jt_extractor = JockeyTrainerFeatureExtractor()
        
        # テストデータ作成
        df = pd.DataFrame({
            "race_id": ["R001"],
            "horse_id": ["H001"],
            "jockey_id": ["J001"],
            "trainer_id": ["T001"],
            "distance": [1600],
            "track_type": ["turf"]
        })
        
        # 各特徴量抽出
        df = perf_extractor.extract_all_performance_features(df)
        df = time_extractor.extract_all_time_features(df)
        df = jt_extractor.extract_all_jockey_trainer_features(df)
        
        # 合計70個の特徴量が生成されることを確認
        total_features = (
            perf_extractor.feature_count +
            time_extractor.feature_count +
            jt_extractor.feature_count
        )
        self.assertEqual(total_features, 70)
        
        print(f"✅ Phase1特徴量テスト完了: 合計{total_features}個の特徴量を確認")


if __name__ == "__main__":
    unittest.main()