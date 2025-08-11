"""データクレンジング機能

欠損値処理、外れ値検出・処理、データ正規化、カテゴリ変数エンコーディングを行う
"""

from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import LabelEncoder, MinMaxScaler, StandardScaler

from src.core.exceptions import DataProcessingError


class DataCleaner:
    """データクレンジングを行うクラス"""

    def __init__(self):
        """初期化"""
        self.scaler = None
        self.label_encoders = {}
        self.imputers = {}

    def handle_missing_values(
        self,
        df: pd.DataFrame,
        strategy: str = "mean",
        columns: Optional[list[str]] = None,
        custom_values: Optional[dict[str, any]] = None,
    ) -> pd.DataFrame:
        """欠損値処理

        Args:
            df: 処理対象のデータフレーム
            strategy: 処理戦略 ('mean', 'median', 'most_frequent', 'constant', 'drop', 'forward_fill')
            columns: 処理対象カラム(Noneの場合は全カラム)
            custom_values: カスタム値での補完用辞書

        Returns:
            欠損値処理後のデータフレーム
        """
        df_processed = df.copy()

        if columns is None:
            columns = df_processed.columns.tolist()

        logger.info(f"欠損値処理開始: strategy={strategy}, columns={len(columns)}")

        try:
            if strategy == "drop":
                # 欠損値を含む行を削除
                df_processed = df_processed.dropna(subset=columns)

            elif strategy == "forward_fill":
                # 前の値で補完
                df_processed[columns] = df_processed[columns].fillna(method="ffill")

            elif custom_values:
                # カスタム値で補完
                for col, value in custom_values.items():
                    if col in columns:
                        df_processed[col] = df_processed[col].fillna(value)

            else:
                # SimpleImputerを使用した補完
                numeric_columns = (
                    df_processed[columns].select_dtypes(include=[np.number]).columns
                )
                categorical_columns = (
                    df_processed[columns].select_dtypes(include=["object"]).columns
                )

                # 数値カラムの処理
                if len(numeric_columns) > 0:
                    if strategy == "constant":
                        imputer = SimpleImputer(strategy="constant", fill_value=0)
                    else:
                        imputer = SimpleImputer(strategy=strategy)

                    df_processed[numeric_columns] = imputer.fit_transform(
                        df_processed[numeric_columns]
                    )
                    self.imputers["numeric"] = imputer

                # カテゴリカラムの処理
                if len(categorical_columns) > 0:
                    if strategy in ["mean", "median"]:
                        cat_strategy = "most_frequent"
                    else:
                        cat_strategy = strategy

                    imputer = SimpleImputer(strategy=cat_strategy)
                    df_processed[categorical_columns] = imputer.fit_transform(
                        df_processed[categorical_columns]
                    )
                    self.imputers["categorical"] = imputer

            missing_after = df_processed[columns].isnull().sum().sum()
            logger.info(f"欠損値処理完了: 残り欠損値数={missing_after}")

            return df_processed

        except Exception as e:
            raise DataProcessingError(
                f"欠損値処理中にエラーが発生しました: {e!s}"
            ) from e

    def detect_outliers(
        self,
        df: pd.DataFrame,
        columns: Optional[list[str]] = None,
        method: str = "iqr",
        threshold: float = 1.5,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """外れ値検出

        Args:
            df: 処理対象のデータフレーム
            columns: 処理対象カラム(Noneの場合は数値カラム全て)
            method: 検出方法 ('iqr', 'zscore', 'isolation_forest')
            threshold: 閾値(IQRの場合は倍率、z-scoreの場合は標準偏差)

        Returns:
            (外れ値フラグのデータフレーム, 外れ値統計情報)
        """
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        outlier_flags = pd.DataFrame(index=df.index)
        outlier_stats = []

        logger.info(f"外れ値検出開始: method={method}, columns={len(columns)}")

        try:
            for col in columns:
                if col not in df.columns:
                    continue

                data = df[col].dropna()

                if method == "iqr":
                    # IQR法による外れ値検出
                    Q1 = data.quantile(0.25)
                    Q3 = data.quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - threshold * IQR
                    upper_bound = Q3 + threshold * IQR

                    outliers = (df[col] < lower_bound) | (df[col] > upper_bound)

                elif method == "zscore":
                    # z-score法による外れ値検出
                    mean = data.mean()
                    std = data.std()
                    z_scores = np.abs((df[col] - mean) / std)
                    outliers = z_scores > threshold

                else:
                    raise ValueError(f"不明な外れ値検出方法: {method}")

                outlier_flags[col] = outliers

                # 統計情報を記録
                n_outliers = outliers.sum()
                outlier_ratio = n_outliers / len(df) * 100

                outlier_stats.append(
                    {
                        "column": col,
                        "n_outliers": n_outliers,
                        "outlier_ratio": outlier_ratio,
                        "method": method,
                        "threshold": threshold,
                    }
                )

                logger.debug(f"{col}: 外れ値 {n_outliers} 件 ({outlier_ratio:.2f}%)")

            stats_df = pd.DataFrame(outlier_stats)
            logger.info(f"外れ値検出完了: 総外れ値数={outlier_flags.sum().sum()}")

            return outlier_flags, stats_df

        except Exception as e:
            raise DataProcessingError(
                f"外れ値検出中にエラーが発生しました: {e!s}"
            ) from e

    def handle_outliers(
        self,
        df: pd.DataFrame,
        outlier_flags: pd.DataFrame,
        method: str = "clip",
        clip_percentile: tuple[float, float] = (1, 99),
    ) -> pd.DataFrame:
        """外れ値処理

        Args:
            df: 処理対象のデータフレーム
            outlier_flags: 外れ値フラグのデータフレーム
            method: 処理方法 ('clip', 'remove', 'replace_mean', 'replace_median')
            clip_percentile: クリッピングのパーセンタイル

        Returns:
            外れ値処理後のデータフレーム
        """
        df_processed = df.copy()

        logger.info(f"外れ値処理開始: method={method}")

        try:
            for col in outlier_flags.columns:
                if col not in df.columns:
                    continue

                outliers = outlier_flags[col]

                if method == "clip":
                    # 指定パーセンタイルでクリッピング
                    lower = df[col].quantile(clip_percentile[0] / 100)
                    upper = df[col].quantile(clip_percentile[1] / 100)
                    df_processed[col] = df_processed[col].clip(lower=lower, upper=upper)

                elif method == "remove":
                    # 外れ値を含む行を削除
                    df_processed = df_processed[~outliers]

                elif method == "replace_mean":
                    # 外れ値を平均値で置換
                    mean_value = df[col][~outliers].mean()
                    df_processed.loc[outliers, col] = mean_value

                elif method == "replace_median":
                    # 外れ値を中央値で置換
                    median_value = df[col][~outliers].median()
                    df_processed.loc[outliers, col] = median_value

                else:
                    raise ValueError(f"不明な外れ値処理方法: {method}")

            logger.info(f"外れ値処理完了: 処理後の行数={len(df_processed)}")

            return df_processed

        except Exception as e:
            raise DataProcessingError(
                f"外れ値処理中にエラーが発生しました: {e!s}"
            ) from e

    def normalize_data(
        self,
        df: pd.DataFrame,
        columns: Optional[list[str]] = None,
        method: str = "standard",
        feature_range: tuple[float, float] = (0, 1),
    ) -> pd.DataFrame:
        """データ正規化

        Args:
            df: 処理対象のデータフレーム
            columns: 処理対象カラム(Noneの場合は数値カラム全て)
            method: 正規化方法 ('standard', 'minmax', 'robust')
            feature_range: MinMaxScalerの範囲

        Returns:
            正規化後のデータフレーム
        """
        df_processed = df.copy()

        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        logger.info(f"データ正規化開始: method={method}, columns={len(columns)}")

        try:
            if method == "standard":
                # 標準化(平均0、標準偏差1)
                scaler = StandardScaler()

            elif method == "minmax":
                # Min-Max正規化
                scaler = MinMaxScaler(feature_range=feature_range)

            elif method == "robust":
                # ロバストスケーリング(中央値と四分位範囲を使用)
                from sklearn.preprocessing import RobustScaler

                scaler = RobustScaler()

            else:
                raise ValueError(f"不明な正規化方法: {method}")

            # 正規化実行
            df_processed[columns] = scaler.fit_transform(df_processed[columns])
            self.scaler = scaler

            logger.info("データ正規化完了")

            return df_processed

        except Exception as e:
            raise DataProcessingError(
                f"データ正規化中にエラーが発生しました: {e!s}"
            ) from e

    def encode_categorical(
        self,
        df: pd.DataFrame,
        columns: Optional[list[str]] = None,
        method: str = "label",
        handle_unknown: str = "error",
    ) -> pd.DataFrame:
        """カテゴリ変数エンコーディング

        Args:
            df: 処理対象のデータフレーム
            columns: 処理対象カラム(Noneの場合はobject型カラム全て)
            method: エンコーディング方法 ('label', 'onehot', 'target')
            handle_unknown: 未知のカテゴリの処理方法

        Returns:
            エンコーディング後のデータフレーム
        """
        df_processed = df.copy()

        if columns is None:
            columns = df.select_dtypes(include=["object"]).columns.tolist()

        logger.info(
            f"カテゴリ変数エンコーディング開始: method={method}, columns={len(columns)}"
        )

        try:
            if method == "label":
                # ラベルエンコーディング
                for col in columns:
                    le = LabelEncoder()
                    df_processed[col] = le.fit_transform(df_processed[col].astype(str))
                    self.label_encoders[col] = le

            elif method == "onehot":
                # One-Hotエンコーディング
                df_processed = pd.get_dummies(
                    df_processed, columns=columns, drop_first=True, dummy_na=False
                )

            elif method == "target":
                # ターゲットエンコーディング(実装は簡略版)
                logger.warning(
                    "ターゲットエンコーディングは未実装です。ラベルエンコーディングを使用します。"
                )
                return self.encode_categorical(df, columns, method="label")

            else:
                raise ValueError(f"不明なエンコーディング方法: {method}")

            logger.info(
                f"カテゴリ変数エンコーディング完了: 処理後のカラム数={len(df_processed.columns)}"
            )

            return df_processed

        except Exception as e:
            raise DataProcessingError(
                f"カテゴリ変数エンコーディング中にエラーが発生しました: {e!s}"
            ) from e

    def clean_data(
        self,
        df: pd.DataFrame,
        missing_strategy: str = "mean",
        outlier_method: str = "iqr",
        outlier_handling: str = "clip",
        normalize_method: str = "standard",
        encode_method: str = "label",
    ) -> pd.DataFrame:
        """データクレンジングの一括実行

        Args:
            df: 処理対象のデータフレーム
            missing_strategy: 欠損値処理戦略
            outlier_method: 外れ値検出方法
            outlier_handling: 外れ値処理方法
            normalize_method: 正規化方法
            encode_method: エンコーディング方法

        Returns:
            クレンジング済みのデータフレーム
        """
        logger.info("データクレンジング開始")

        try:
            # 1. 欠損値処理
            df_cleaned = self.handle_missing_values(df, strategy=missing_strategy)

            # 2. 外れ値検出・処理
            numeric_columns = df_cleaned.select_dtypes(
                include=[np.number]
            ).columns.tolist()
            if numeric_columns:
                outlier_flags, _ = self.detect_outliers(
                    df_cleaned, columns=numeric_columns, method=outlier_method
                )
                df_cleaned = self.handle_outliers(
                    df_cleaned, outlier_flags, method=outlier_handling
                )

            # 3. カテゴリ変数エンコーディング
            categorical_columns = df_cleaned.select_dtypes(
                include=["object"]
            ).columns.tolist()
            if categorical_columns:
                df_cleaned = self.encode_categorical(
                    df_cleaned, columns=categorical_columns, method=encode_method
                )

            # 4. データ正規化
            numeric_columns = df_cleaned.select_dtypes(
                include=[np.number]
            ).columns.tolist()
            if numeric_columns:
                df_cleaned = self.normalize_data(
                    df_cleaned, columns=numeric_columns, method=normalize_method
                )

            logger.info(f"データクレンジング完了: shape={df_cleaned.shape}")

            return df_cleaned

        except Exception as e:
            raise DataProcessingError(
                f"データクレンジング中にエラーが発生しました: {e!s}"
            ) from e
