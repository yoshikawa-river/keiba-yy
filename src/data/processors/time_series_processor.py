"""時系列データ処理機能

日付データの標準化、時系列特徴量の生成、ラグ特徴量の作成を行う
"""

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from src.core.exceptions import DataProcessingError


class TimeSeriesProcessor:
    """時系列データ処理を行うクラス"""

    def __init__(self):
        """初期化"""
        self.date_columns = []
        self.time_features = []

    def standardize_dates(
        self,
        df: pd.DataFrame,
        date_columns: Optional[list[str]] = None,
        target_timezone: str = "Asia/Tokyo",
        infer_format: bool = True,
    ) -> pd.DataFrame:
        """日付データの標準化

        Args:
            df: 処理対象のデータフレーム
            date_columns: 日付カラムのリスト(Noneの場合は自動検出)
            target_timezone: 目標タイムゾーン
            infer_format: 日付フォーマットを自動推定するか

        Returns:
            日付標準化後のデータフレーム
        """
        df_processed = df.copy()

        # 日付カラムの自動検出
        if date_columns is None:
            date_columns = self._detect_date_columns(df_processed)

        self.date_columns = date_columns
        logger.info(f"日付データ標準化開始: columns={date_columns}")

        try:
            for col in date_columns:
                if col not in df_processed.columns:
                    continue

                # datetime型に変換
                if not pd.api.types.is_datetime64_any_dtype(df_processed[col]):
                    df_processed[col] = pd.to_datetime(
                        df_processed[col],
                        infer_datetime_format=infer_format,
                        errors="coerce",
                    )

                # タイムゾーンの設定
                if df_processed[col].dt.tz is None:
                    df_processed[col] = df_processed[col].dt.tz_localize(
                        target_timezone
                    )
                else:
                    df_processed[col] = df_processed[col].dt.tz_convert(target_timezone)

                # 欠損値の数をログ出力
                n_missing = df_processed[col].isnull().sum()
                if n_missing > 0:
                    logger.warning(f"{col}: {n_missing}件の日付変換エラー")

            logger.info("日付データ標準化完了")
            return df_processed

        except Exception as e:
            raise DataProcessingError(
                f"日付データ標準化中にエラーが発生しました: {e!s}"
            ) from e

    def _detect_date_columns(self, df: pd.DataFrame) -> list[str]:
        """日付カラムの自動検出

        Args:
            df: データフレーム

        Returns:
            日付カラムのリスト
        """
        date_columns = []

        # datetime型のカラムを検出
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                date_columns.append(col)
                continue

            # 文字列型で日付パターンを含むカラムを検出
            if df[col].dtype == "object":
                # サンプルデータで日付変換を試みる
                sample = df[col].dropna().head(100)
                if len(sample) > 0:
                    try:
                        pd.to_datetime(sample, errors="coerce")
                        # 変換成功率が80%以上なら日付カラムとみなす
                        success_rate = pd.to_datetime(
                            sample, errors="coerce"
                        ).notna().sum() / len(sample)
                        if success_rate > 0.8:
                            date_columns.append(col)
                    except Exception:
                        pass

        # カラム名から推測
        date_keywords = ["date", "time", "日付", "時刻", "年月日", "_at", "_on"]
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in date_keywords):
                if col not in date_columns:
                    date_columns.append(col)

        return date_columns

    def create_time_features(
        self, df: pd.DataFrame, date_column: str, features: Optional[list[str]] = None
    ) -> pd.DataFrame:
        """時系列特徴量の生成

        Args:
            df: 処理対象のデータフレーム
            date_column: 基準となる日付カラム
            features: 生成する特徴量のリスト

        Returns:
            特徴量追加後のデータフレーム
        """
        if features is None:
            features = [
                "year",
                "month",
                "day",
                "dayofweek",
                "dayofyear",
                "weekofyear",
                "quarter",
                "is_weekend",
                "is_month_start",
                "is_month_end",
                "is_quarter_start",
                "is_quarter_end",
            ]

        df_processed = df.copy()

        logger.info(
            f"時系列特徴量生成開始: base_column={date_column}, features={len(features)}"
        )

        try:
            # datetime型でない場合は変換
            if not pd.api.types.is_datetime64_any_dtype(df_processed[date_column]):
                df_processed[date_column] = pd.to_datetime(df_processed[date_column])

            dt = df_processed[date_column].dt

            # 基本的な時間特徴量
            if "year" in features:
                df_processed[f"{date_column}_year"] = dt.year
            if "month" in features:
                df_processed[f"{date_column}_month"] = dt.month
            if "day" in features:
                df_processed[f"{date_column}_day"] = dt.day
            if "dayofweek" in features:
                df_processed[f"{date_column}_dayofweek"] = dt.dayofweek
            if "dayofyear" in features:
                df_processed[f"{date_column}_dayofyear"] = dt.dayofyear
            if "weekofyear" in features:
                df_processed[f"{date_column}_weekofyear"] = dt.isocalendar().week
            if "quarter" in features:
                df_processed[f"{date_column}_quarter"] = dt.quarter

            # 追加の特徴量
            if "is_weekend" in features:
                df_processed[f"{date_column}_is_weekend"] = (dt.dayofweek >= 5).astype(
                    int
                )
            if "is_month_start" in features:
                df_processed[f"{date_column}_is_month_start"] = (
                    dt.is_month_start.astype(int)
                )
            if "is_month_end" in features:
                df_processed[f"{date_column}_is_month_end"] = dt.is_month_end.astype(
                    int
                )
            if "is_quarter_start" in features:
                df_processed[f"{date_column}_is_quarter_start"] = (
                    dt.is_quarter_start.astype(int)
                )
            if "is_quarter_end" in features:
                df_processed[f"{date_column}_is_quarter_end"] = (
                    dt.is_quarter_end.astype(int)
                )

            # 時間帯特徴量(時刻情報がある場合)
            if "hour" in features and not pd.isnull(dt.hour).all():
                df_processed[f"{date_column}_hour"] = dt.hour
            if "minute" in features and not pd.isnull(dt.minute).all():
                df_processed[f"{date_column}_minute"] = dt.minute

            # 周期的特徴量(サイン・コサイン変換)
            if "month_sin" in features:
                df_processed[f"{date_column}_month_sin"] = np.sin(
                    2 * np.pi * dt.month / 12
                )
            if "month_cos" in features:
                df_processed[f"{date_column}_month_cos"] = np.cos(
                    2 * np.pi * dt.month / 12
                )
            if "day_sin" in features:
                df_processed[f"{date_column}_day_sin"] = np.sin(2 * np.pi * dt.day / 31)
            if "day_cos" in features:
                df_processed[f"{date_column}_day_cos"] = np.cos(2 * np.pi * dt.day / 31)
            if "dayofweek_sin" in features:
                df_processed[f"{date_column}_dayofweek_sin"] = np.sin(
                    2 * np.pi * dt.dayofweek / 7
                )
            if "dayofweek_cos" in features:
                df_processed[f"{date_column}_dayofweek_cos"] = np.cos(
                    2 * np.pi * dt.dayofweek / 7
                )

            self.time_features.extend(
                [
                    f"{date_column}_{feat}"
                    for feat in features
                    if f"{date_column}_{feat}" in df_processed.columns
                ]
            )

            logger.info(f"時系列特徴量生成完了: 新規特徴量数={len(self.time_features)}")

            return df_processed

        except Exception as e:
            raise DataProcessingError(
                f"時系列特徴量生成中にエラーが発生しました: {e!s}"
            ) from e

    def create_lag_features(
        self,
        df: pd.DataFrame,
        target_columns: list[str],
        lag_periods: list[int],
        date_column: Optional[str] = None,
        group_columns: Optional[list[str]] = None,
    ) -> pd.DataFrame:
        """ラグ特徴量の作成

        Args:
            df: 処理対象のデータフレーム
            target_columns: ラグ特徴量を作成する対象カラム
            lag_periods: ラグ期間のリスト(例:[1, 7, 30])
            date_column: 時系列順序の基準となる日付カラム
            group_columns: グループ化するカラム(例:馬ID)

        Returns:
            ラグ特徴量追加後のデータフレーム
        """
        df_processed = df.copy()

        # 日付カラムでソート
        if date_column:
            df_processed = df_processed.sort_values(date_column)

        logger.info(
            f"ラグ特徴量作成開始: target_columns={len(target_columns)}, lag_periods={lag_periods}"
        )

        try:
            for col in target_columns:
                if col not in df_processed.columns:
                    continue

                for lag in lag_periods:
                    lag_col_name = f"{col}_lag_{lag}"

                    if group_columns:
                        # グループごとにラグ特徴量を作成
                        df_processed[lag_col_name] = df_processed.groupby(
                            group_columns
                        )[col].shift(lag)
                    else:
                        # 全体でラグ特徴量を作成
                        df_processed[lag_col_name] = df_processed[col].shift(lag)

                    logger.debug(f"作成: {lag_col_name}")

            # 移動平均特徴量
            for col in target_columns:
                if col not in df_processed.columns:
                    continue

                # 移動平均ウィンドウ
                windows = [3, 7, 14, 30]

                for window in windows:
                    if window > max(lag_periods):
                        continue

                    ma_col_name = f"{col}_ma_{window}"

                    if group_columns:
                        df_processed[ma_col_name] = df_processed.groupby(group_columns)[
                            col
                        ].transform(
                            lambda x, w=window: x.rolling(
                                window=w, min_periods=1
                            ).mean()
                        )
                    else:
                        df_processed[ma_col_name] = (
                            df_processed[col]
                            .rolling(window=window, min_periods=1)
                            .mean()
                        )

                    logger.debug(f"作成: {ma_col_name}")

            logger.info("ラグ特徴量作成完了")

            return df_processed

        except Exception as e:
            raise DataProcessingError(
                f"ラグ特徴量作成中にエラーが発生しました: {e!s}"
            ) from e

    def create_time_diff_features(
        self,
        df: pd.DataFrame,
        date_column: str,
        reference_dates: Optional[dict[str, str | datetime]] = None,
        group_column: Optional[str] = None,
    ) -> pd.DataFrame:
        """時間差特徴量の作成

        Args:
            df: 処理対象のデータフレーム
            date_column: 基準となる日付カラム
            reference_dates: 参照日付の辞書(例:{'last_race': '2024-01-01'})
            group_column: グループ化するカラム(例:馬ID)

        Returns:
            時間差特徴量追加後のデータフレーム
        """
        df_processed = df.copy()

        logger.info(f"時間差特徴量作成開始: date_column={date_column}")

        try:
            # datetime型でない場合は変換
            if not pd.api.types.is_datetime64_any_dtype(df_processed[date_column]):
                df_processed[date_column] = pd.to_datetime(df_processed[date_column])

            # 前のレコードとの時間差
            if group_column:
                df_processed[f"{date_column}_diff_days"] = (
                    df_processed.groupby(group_column)[date_column].diff().dt.days
                )
                df_processed[f"{date_column}_diff_hours"] = (
                    df_processed.groupby(group_column)[date_column]
                    .diff()
                    .dt.total_seconds()
                    / 3600
                )
            else:
                df_processed[f"{date_column}_diff_days"] = (
                    df_processed[date_column].diff().dt.days
                )
                df_processed[f"{date_column}_diff_hours"] = (
                    df_processed[date_column].diff().dt.total_seconds() / 3600
                )

            # 参照日付との時間差
            if reference_dates:
                for ref_name, ref_date in reference_dates.items():
                    if isinstance(ref_date, str):
                        ref_date = pd.to_datetime(ref_date)

                    df_processed[f"{date_column}_from_{ref_name}_days"] = (
                        df_processed[date_column] - ref_date
                    ).dt.days
                    df_processed[f"{date_column}_from_{ref_name}_months"] = (
                        (df_processed[date_column] - ref_date).dt.days / 30.44
                    ).round(1)

            # 統計的時間差特徴量(グループごと)
            if group_column:
                # 平均間隔
                mean_diff = df_processed.groupby(group_column)[
                    f"{date_column}_diff_days"
                ].transform("mean")
                df_processed[f"{date_column}_diff_from_mean"] = (
                    df_processed[f"{date_column}_diff_days"] - mean_diff
                )

                # 最小・最大間隔
                df_processed[f"{date_column}_min_diff"] = df_processed.groupby(
                    group_column
                )[f"{date_column}_diff_days"].transform("min")
                df_processed[f"{date_column}_max_diff"] = df_processed.groupby(
                    group_column
                )[f"{date_column}_diff_days"].transform("max")

            logger.info("時間差特徴量作成完了")

            return df_processed

        except Exception as e:
            raise DataProcessingError(
                f"時間差特徴量作成中にエラーが発生しました: {e!s}"
            ) from e

    def create_seasonal_features(
        self, df: pd.DataFrame, date_column: str, country: str = "JP"
    ) -> pd.DataFrame:
        """季節性特徴量の作成

        Args:
            df: 処理対象のデータフレーム
            date_column: 基準となる日付カラム
            country: 国コード(祝日の判定用)

        Returns:
            季節性特徴量追加後のデータフレーム
        """
        df_processed = df.copy()

        logger.info(f"季節性特徴量作成開始: date_column={date_column}")

        try:
            # datetime型でない場合は変換
            if not pd.api.types.is_datetime64_any_dtype(df_processed[date_column]):
                df_processed[date_column] = pd.to_datetime(df_processed[date_column])

            dt = df_processed[date_column].dt

            # 季節の判定(日本の場合)
            def get_season(month):
                if month in [3, 4, 5]:
                    return "spring"
                if month in [6, 7, 8]:
                    return "summer"
                if month in [9, 10, 11]:
                    return "autumn"
                return "winter"

            df_processed[f"{date_column}_season"] = dt.month.apply(get_season)

            # 祝日判定(簡易版)
            # 実際のプロジェクトではjpholidayなどのライブラリを使用
            df_processed[f"{date_column}_is_holiday"] = 0  # デフォルトは平日

            # 年末年始フラグ
            df_processed[f"{date_column}_is_year_end"] = (
                ((dt.month == 12) & (dt.day >= 28)) | ((dt.month == 1) & (dt.day <= 3))
            ).astype(int)

            # ゴールデンウィークフラグ
            df_processed[f"{date_column}_is_golden_week"] = (
                (dt.month == 5) & (dt.day >= 3) & (dt.day <= 5)
            ).astype(int)

            # お盆フラグ
            df_processed[f"{date_column}_is_obon"] = (
                (dt.month == 8) & (dt.day >= 13) & (dt.day <= 16)
            ).astype(int)

            logger.info("季節性特徴量作成完了")

            return df_processed

        except Exception as e:
            raise DataProcessingError(
                f"季節性特徴量作成中にエラーが発生しました: {e!s}"
            ) from e
