"""基本特徴量抽出機能

馬齢、性別、斤量、馬体重、枠番、馬番、前走からの間隔などの基本特徴量を抽出する
"""

import pandas as pd
from loguru import logger

from src.core.exceptions import FeatureExtractionError


class BaseFeatureExtractor:
    """基本特徴量を抽出するクラス"""

    def __init__(self):
        """初期化"""
        self.feature_names = []
        self.feature_count = 0  # 特徴量カウント管理
        self.categorical_features = []
        self.numerical_features = []

    def extract_horse_basic_features(
        self, df: pd.DataFrame, horse_info: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """馬の基本特徴量抽出

        Args:
            df: レースデータフレーム
            horse_info: 馬情報データフレーム(追加情報がある場合)

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("馬の基本特徴量抽出開始")

        try:
            df_features = df.copy()

            # 馬齢
            if "horse_age" in df.columns:
                df_features["horse_age"] = df["horse_age"].astype(float)
                # 馬齢カテゴリ(若馬、成馬、高齢馬)
                df_features["horse_age_category"] = pd.cut(
                    df["horse_age"],
                    bins=[0, 3, 6, 100],
                    labels=["young", "prime", "veteran"],
                )
                self.numerical_features.append("horse_age")
                self.categorical_features.append("horse_age_category")

            # 性別
            if "horse_sex" in df.columns:
                df_features["horse_sex_encoded"] = self._encode_sex(df["horse_sex"])
                # 性別ダミー変数
                sex_dummies = pd.get_dummies(df["horse_sex"], prefix="sex")
                df_features = pd.concat([df_features, sex_dummies], axis=1)
                self.categorical_features.append("horse_sex_encoded")
                self.categorical_features.extend(sex_dummies.columns.tolist())

            # 斤量(負担重量)
            if "weight_carried" in df.columns:
                df_features["weight_carried"] = df["weight_carried"].astype(float)
                # 斤量の標準化(平均との差)
                mean_weight = df["weight_carried"].mean()
                df_features["weight_carried_diff"] = df["weight_carried"] - mean_weight
                # 斤量カテゴリ
                df_features["weight_carried_category"] = pd.cut(
                    df["weight_carried"],
                    bins=[0, 54, 56, 58, 100],
                    labels=["light", "standard", "heavy", "very_heavy"],
                )
                self.numerical_features.extend(
                    ["weight_carried", "weight_carried_diff"]
                )
                self.categorical_features.append("weight_carried_category")

            # 馬体重
            if "horse_weight" in df.columns:
                df_features["horse_weight"] = df["horse_weight"].astype(float)
                # 馬体重変化
                if "horse_weight_diff" in df.columns:
                    df_features["horse_weight_diff"] = df["horse_weight_diff"].astype(
                        float
                    )
                    # 体重変化率
                    df_features["horse_weight_change_rate"] = (
                        df["horse_weight_diff"] / df["horse_weight"] * 100
                    )
                    # 体重変化カテゴリ
                    df_features["weight_change_category"] = pd.cut(
                        df["horse_weight_diff"],
                        bins=[-100, -10, -5, 5, 10, 100],
                        labels=["large_loss", "loss", "stable", "gain", "large_gain"],
                    )
                    self.numerical_features.extend(
                        ["horse_weight_diff", "horse_weight_change_rate"]
                    )
                    self.categorical_features.append("weight_change_category")

                # 体重カテゴリ
                df_features["horse_weight_category"] = pd.cut(
                    df["horse_weight"],
                    bins=[0, 440, 480, 520, 1000],
                    labels=["light", "standard", "heavy", "very_heavy"],
                )
                self.numerical_features.append("horse_weight")
                self.categorical_features.append("horse_weight_category")

            # 枠番・馬番
            if "post_position" in df.columns:
                df_features["post_position"] = df["post_position"].astype(int)
                # 内枠・中枠・外枠のカテゴリ
                df_features["post_category"] = pd.cut(
                    df["post_position"],
                    bins=[0, 4, 12, 20],
                    labels=["inner", "middle", "outer"],
                )
                self.numerical_features.append("post_position")
                self.categorical_features.append("post_category")

            if "horse_number" in df.columns:
                df_features["horse_number"] = df["horse_number"].astype(int)
                self.numerical_features.append("horse_number")

            # 出走頭数との相対位置
            if "field_size" in df.columns and "post_position" in df.columns:
                df_features["post_position_ratio"] = (
                    df["post_position"] / df["field_size"]
                )
                df_features["is_widest_post"] = (
                    df["post_position"] == df["field_size"]
                ).astype(int)
                self.numerical_features.append("post_position_ratio")
                self.categorical_features.append("is_widest_post")

            # 前走からの間隔
            if "days_since_last_race" in df.columns:
                df_features["days_since_last_race"] = df["days_since_last_race"].astype(
                    float
                )
                # 間隔カテゴリ
                df_features["rest_category"] = pd.cut(
                    df["days_since_last_race"],
                    bins=[0, 14, 28, 56, 180, 10000],
                    labels=["short", "normal", "medium", "long", "very_long"],
                )
                # 休養明けフラグ
                df_features["is_fresh"] = (df["days_since_last_race"] > 90).astype(int)
                self.numerical_features.append("days_since_last_race")
                self.categorical_features.extend(["rest_category", "is_fresh"])

            # 初出走フラグ
            if "career_starts" in df.columns:
                df_features["is_debut"] = (df["career_starts"] == 0).astype(int)
                self.categorical_features.append("is_debut")

            logger.info(
                f"馬の基本特徴量抽出完了: 数値特徴量={len(self.numerical_features)}, カテゴリ特徴量={len(self.categorical_features)}"
            )

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"馬の基本特徴量抽出中にエラーが発生しました: {e!s}"
            ) from e

    def extract_jockey_trainer_features(
        self,
        df: pd.DataFrame,
        jockey_stats: pd.DataFrame | None = None,
        trainer_stats: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """騎手・調教師の特徴量抽出

        Args:
            df: レースデータフレーム
            jockey_stats: 騎手統計データフレーム
            trainer_stats: 調教師統計データフレーム

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("騎手・調教師の特徴量抽出開始")

        try:
            df_features = df.copy()

            # 騎手ID
            if "jockey_id" in df.columns:
                # 騎手の経験値(仮の実装)
                if jockey_stats is not None and "jockey_id" in jockey_stats.columns:
                    # 騎手統計をマージ
                    jockey_cols = [
                        "jockey_id",
                        "着順_win_rate",
                        "着順_place_rate",
                        "着順_show_rate",
                    ]
                    jockey_cols = [c for c in jockey_cols if c in jockey_stats.columns]
                    if len(jockey_cols) > 1:
                        df_features = df_features.merge(
                            jockey_stats[jockey_cols],
                            on="jockey_id",
                            how="left",
                            suffixes=("", "_jockey"),
                        )
                        self.numerical_features.extend(jockey_cols[1:])

                # 騎手カテゴリ(簡易版:IDベース)
                df_features["jockey_category"] = pd.qcut(
                    df["jockey_id"].fillna(0),
                    q=5,
                    labels=["rookie", "junior", "middle", "senior", "veteran"],
                    duplicates="drop",
                )
                self.categorical_features.append("jockey_category")

            # 調教師ID
            if "trainer_id" in df.columns:
                # 調教師の経験値(仮の実装)
                if trainer_stats is not None and "trainer_id" in trainer_stats.columns:
                    # 調教師統計をマージ
                    trainer_cols = [
                        "trainer_id",
                        "着順_win_rate",
                        "着順_place_rate",
                        "着順_show_rate",
                    ]
                    trainer_cols = [
                        c for c in trainer_cols if c in trainer_stats.columns
                    ]
                    if len(trainer_cols) > 1:
                        df_features = df_features.merge(
                            trainer_stats[trainer_cols],
                            on="trainer_id",
                            how="left",
                            suffixes=("", "_trainer"),
                        )
                        self.numerical_features.extend(trainer_cols[1:])

                # 調教師カテゴリ(簡易版:IDベース)
                df_features["trainer_category"] = pd.qcut(
                    df["trainer_id"].fillna(0),
                    q=5,
                    labels=["new", "developing", "established", "experienced", "elite"],
                    duplicates="drop",
                )
                self.categorical_features.append("trainer_category")

            # 騎手と調教師のコンビネーション
            if "jockey_id" in df.columns and "trainer_id" in df.columns:
                df_features["jockey_trainer_combo"] = (
                    df["jockey_id"].astype(str) + "_" + df["trainer_id"].astype(str)
                )
                # コンビネーションの頻度(同一レース内)
                combo_counts = df_features.groupby(
                    ["race_id", "jockey_trainer_combo"]
                ).size()
                df_features["combo_frequency"] = df_features.apply(
                    lambda x: combo_counts.get(
                        (x["race_id"], x["jockey_trainer_combo"]), 0
                    )
                    if "race_id" in x
                    else 0,
                    axis=1,
                )
                self.categorical_features.append("jockey_trainer_combo")
                self.numerical_features.append("combo_frequency")

            logger.info("騎手・調教師の特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"騎手・調教師の特徴量抽出中にエラーが発生しました: {e!s}"
            ) from e

    def extract_race_condition_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """レース条件の特徴量抽出

        Args:
            df: レースデータフレーム

        Returns:
            特徴量追加後のデータフレーム
        """
        logger.info("レース条件の特徴量抽出開始")

        try:
            df_features = df.copy()

            # 距離
            if "distance" in df.columns:
                df_features["distance"] = df["distance"].astype(float)
                # 距離カテゴリ
                df_features["distance_category"] = pd.cut(
                    df["distance"],
                    bins=[0, 1400, 1800, 2200, 4000],
                    labels=["sprint", "mile", "intermediate", "long"],
                )
                # 距離の2乗(非線形効果)
                df_features["distance_squared"] = df["distance"] ** 2
                self.numerical_features.extend(["distance", "distance_squared"])
                self.categorical_features.append("distance_category")

            # コース種別(芝・ダート)
            if "track_type" in df.columns:
                df_features["track_type_encoded"] = df["track_type"].map(
                    {"turf": 0, "dirt": 1}
                )
                track_dummies = pd.get_dummies(df["track_type"], prefix="track")
                df_features = pd.concat([df_features, track_dummies], axis=1)
                self.numerical_features.append("track_type_encoded")
                self.categorical_features.extend(track_dummies.columns.tolist())

            # 馬場状態
            if "track_condition" in df.columns:
                condition_map = {
                    "firm": 1,
                    "good": 2,
                    "yielding": 3,
                    "soft": 4,
                    "heavy": 5,
                }
                df_features["track_condition_encoded"] = df["track_condition"].map(
                    condition_map
                )
                condition_dummies = pd.get_dummies(
                    df["track_condition"], prefix="condition"
                )
                df_features = pd.concat([df_features, condition_dummies], axis=1)
                self.numerical_features.append("track_condition_encoded")
                self.categorical_features.extend(condition_dummies.columns.tolist())

            # 天候
            if "weather" in df.columns:
                weather_dummies = pd.get_dummies(df["weather"], prefix="weather")
                df_features = pd.concat([df_features, weather_dummies], axis=1)
                self.categorical_features.extend(weather_dummies.columns.tolist())

            # レースクラス
            if "race_class" in df.columns:
                # クラスのランク付け(簡易版)
                class_rank = {
                    "G1": 8,
                    "G2": 7,
                    "G3": 6,
                    "オープン": 5,
                    "OP": 5,
                    "3勝": 4,
                    "1600万": 4,
                    "2勝": 3,
                    "1000万": 3,
                    "1勝": 2,
                    "500万": 2,
                    "新馬": 1,
                    "未勝利": 1,
                }
                df_features["race_class_rank"] = (
                    df["race_class"].map(class_rank).fillna(0)
                )
                self.numerical_features.append("race_class_rank")

            # レース時刻(午前・午後)
            if "race_time" in df.columns:
                # 時刻から時間帯を抽出
                df_features["race_hour"] = pd.to_datetime(df["race_time"]).dt.hour
                df_features["is_afternoon"] = (df_features["race_hour"] >= 12).astype(
                    int
                )
                df_features["time_category"] = pd.cut(
                    df_features["race_hour"],
                    bins=[0, 12, 15, 24],
                    labels=["morning", "afternoon", "evening"],
                )
                self.numerical_features.append("race_hour")
                self.categorical_features.extend(["is_afternoon", "time_category"])

            # 競馬場
            if "racecourse" in df.columns:
                # 競馬場ダミー変数
                course_dummies = pd.get_dummies(df["racecourse"], prefix="course")
                df_features = pd.concat([df_features, course_dummies], axis=1)
                self.categorical_features.extend(course_dummies.columns.tolist())

                # 東西の区分
                east_courses = ["札幌", "函館", "福島", "新潟", "東京", "中山"]
                df_features["is_east_course"] = (
                    df["racecourse"].isin(east_courses).astype(int)
                )
                self.categorical_features.append("is_east_course")

            # 出走頭数
            if "field_size" in df.columns:
                df_features["field_size"] = df["field_size"].astype(int)
                # 頭数カテゴリ
                df_features["field_size_category"] = pd.cut(
                    df["field_size"],
                    bins=[0, 10, 14, 18],
                    labels=["small", "medium", "large"],
                )
                self.numerical_features.append("field_size")
                self.categorical_features.append("field_size_category")

            logger.info("レース条件の特徴量抽出完了")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"レース条件の特徴量抽出中にエラーが発生しました: {e!s}"
            ) from e

    def _encode_sex(self, sex_series: pd.Series) -> pd.Series:
        """性別のエンコーディング

        Args:
            sex_series: 性別のシリーズ

        Returns:
            エンコード済みシリーズ
        """
        sex_map = {
            "牡": 1,  # 牡馬
            "牝": 2,  # 牝馬
            "セ": 3,  # セン馬
            "male": 1,
            "female": 2,
            "gelding": 3,
        }
        return sex_series.map(sex_map).fillna(0)

    def extract_all_base_features(
        self,
        df: pd.DataFrame,
        horse_info: pd.DataFrame | None = None,
        jockey_stats: pd.DataFrame | None = None,
        trainer_stats: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """全ての基本特徴量を抽出

        Args:
            df: レースデータフレーム
            horse_info: 馬情報データフレーム
            jockey_stats: 騎手統計データフレーム
            trainer_stats: 調教師統計データフレーム

        Returns:
            全特徴量追加後のデータフレーム
        """
        logger.info("全基本特徴量抽出開始")

        try:
            # 馬の基本特徴量
            df_features = self.extract_horse_basic_features(df, horse_info)

            # 騎手・調教師の特徴量
            df_features = self.extract_jockey_trainer_features(
                df_features, jockey_stats, trainer_stats
            )

            # レース条件の特徴量
            df_features = self.extract_race_condition_features(df_features)

            # 特徴量リストの更新
            self.feature_names = self.numerical_features + self.categorical_features
            self.feature_count = len(self.feature_names)

            logger.info(
                f"✅ 基本特徴量抽出完了: 合計{self.feature_count}個の特徴量を生成"
            )
            logger.info(
                f"数値特徴量: {len(self.numerical_features)}個, カテゴリ特徴量: {len(self.categorical_features)}個"
            )
            logger.info(f"生成された特徴量: {self.feature_names}")

            return df_features

        except Exception as e:
            raise FeatureExtractionError(
                f"全基本特徴量抽出中にエラーが発生しました: {e!s}"
            ) from e

    def get_feature_info(self) -> dict[str, list[str]]:
        """特徴量情報の取得

        Returns:
            特徴量タイプ別のリスト
        """
        return {
            "feature_names": self.feature_names,
            "feature_count": self.feature_count,
            "numerical_features": self.numerical_features,
            "categorical_features": self.categorical_features,
            "categories": [
                "馬基本情報特徴量",
                "騎手・調教師特徴量",
                "レース条件特徴量",
            ],
        }
