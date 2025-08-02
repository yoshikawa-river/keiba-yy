"""
CSVパーサーの基底クラス

全てのCSVパーサーが継承する抽象基底クラスを定義
"""

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from src.core.exceptions import DataImportError, ValidationError
from src.core.logging import log_execution_time, logger
from src.data.importers.file_detector import CSVFile


class BaseCSVParser(ABC):
    """CSVパーサーの基底クラス"""

    def __init__(self, db_session: Session):
        """
        パーサーの初期化

        Args:
            db_session: データベースセッション
        """
        self.db_session = db_session
        self.column_mappings = self._get_column_mappings()
        self.required_columns = self._get_required_columns()
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self._init_statistics()

    def _init_statistics(self) -> None:
        """統計情報の初期化"""
        self.statistics = {
            "total_rows": 0,
            "success_count": 0,
            "error_count": 0,
            "warning_count": 0,
            "skip_count": 0,
            "insert_count": 0,
            "update_count": 0,
        }

    @abstractmethod
    def _get_column_mappings(self) -> dict[str, str]:
        """
        CSVカラムとDBカラムのマッピングを定義

        Returns:
            {CSVカラム名: DBカラム名}のマッピング辞書
        """
        pass

    @abstractmethod
    def _get_required_columns(self) -> list[str]:
        """
        必須カラムのリストを定義

        Returns:
            必須カラム名のリスト(CSV側のカラム名)
        """
        pass

    @abstractmethod
    def _transform_row(self, row: pd.Series) -> dict[str, Any]:
        """
        行データを変換

        Args:
            row: パンダスのSeriesオブジェクト

        Returns:
            変換後のデータ辞書

        Raises:
            ValidationError: データ変換エラー
        """
        pass

    @abstractmethod
    def _validate_row(self, row: dict[str, Any]) -> tuple[bool, str | None]:
        """
        行データをバリデーション

        Args:
            row: 変換後のデータ辞書

        Returns:
            (バリデーション成功フラグ, エラーメッセージ)
        """
        pass

    @abstractmethod
    def _save_row(self, row: dict[str, Any]) -> bool:
        """
        行データをデータベースに保存

        Args:
            row: 保存するデータ

        Returns:
            保存成功フラグ
        """
        pass

    @log_execution_time
    def parse_file(
        self, csv_file: CSVFile, batch_size: int = 1000, dry_run: bool = False
    ) -> dict[str, Any]:
        """
        CSVファイルをパース

        Args:
            csv_file: CSVファイル情報
            batch_size: バッチサイズ
            dry_run: ドライラン(DBに保存しない)

        Returns:
            パース結果の統計情報

        Raises:
            DataImportError: インポートエラー
        """
        logger.info(f"パース開始: {csv_file.path.name} (dry_run={dry_run})")
        self._init_statistics()

        try:
            # 必須カラムの確認
            self._validate_columns(csv_file.headers)

            # データ読み込み
            df = self._read_csv(csv_file)
            self.statistics["total_rows"] = len(df)

            # バッチ処理
            for start_idx in range(0, len(df), batch_size):
                end_idx = min(start_idx + batch_size, len(df))
                batch_df = df.iloc[start_idx:end_idx]

                self._process_batch(batch_df, dry_run)

                # 進捗ログ
                progress = end_idx / len(df) * 100
                logger.info(
                    f"進捗: {end_idx}/{len(df)} ({progress:.1f}%) - "
                    f"成功: {self.statistics['success_count']}, "
                    f"エラー: {self.statistics['error_count']}"
                )

            # コミット(ドライランでない場合)
            if not dry_run:
                self.db_session.commit()
                logger.info("データベースへのコミット完了")

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"パースエラー: {e}")
            raise DataImportError(f"ファイルパースに失敗: {csv_file.path.name}") from e

        # 結果サマリー
        self._log_summary()

        return {
            "statistics": self.statistics,
            "errors": self.errors[:100],  # 最初の100件のみ
            "warnings": self.warnings[:100],  # 最初の100件のみ
        }

    def _validate_columns(self, headers: list[str]) -> None:
        """
        必須カラムの存在確認

        Args:
            headers: CSVのヘッダーリスト

        Raises:
            ValidationError: 必須カラムが不足
        """
        missing_columns = set(self.required_columns) - set(headers)
        if missing_columns:
            raise ValidationError(
                f"必須カラムが不足: {', '.join(missing_columns)}",
                {"missing_columns": list(missing_columns)},
            )

    def _read_csv(self, csv_file: CSVFile) -> pd.DataFrame:
        """
        CSVファイルを読み込み

        Args:
            csv_file: CSVファイル情報

        Returns:
            読み込んだDataFrame
        """
        # データ型の推論を無効化し、全て文字列として読み込む
        df = pd.read_csv(
            csv_file.path,
            encoding=csv_file.encoding,
            delimiter=csv_file.delimiter,
            dtype=str,
            na_values=["", "NA", "N/A", "-", "NULL"],
            keep_default_na=True,
        )

        # カラム名の正規化(前後の空白除去)
        df.columns = df.columns.str.strip()

        # カラムマッピングの適用
        columns_to_rename = {
            k: v for k, v in self.column_mappings.items() if k in df.columns
        }
        df = df.rename(columns=columns_to_rename)

        return df

    def _process_batch(self, batch_df: pd.DataFrame, dry_run: bool) -> None:
        """
        バッチ単位でデータを処理

        Args:
            batch_df: バッチデータ
            dry_run: ドライランフラグ
        """
        for idx, row in batch_df.iterrows():
            try:
                # データ変換
                transformed_data = self._transform_row(row)

                # バリデーション
                is_valid, error_message = self._validate_row(transformed_data)

                if not is_valid:
                    self._add_error(
                        idx, error_message or "バリデーションエラー", row.to_dict()
                    )
                    self.statistics["error_count"] += 1
                    continue

                # 保存(ドライランでない場合)
                if not dry_run:
                    if self._save_row(transformed_data):
                        self.statistics["success_count"] += 1
                    else:
                        self.statistics["error_count"] += 1
                        self._add_error(idx, "保存に失敗", transformed_data)
                else:
                    # ドライランの場合は成功とみなす
                    self.statistics["success_count"] += 1

            except ValidationError as e:
                self._add_error(idx, str(e), row.to_dict())
                self.statistics["error_count"] += 1
            except Exception as e:
                self._add_error(idx, f"予期しないエラー: {e}", row.to_dict())
                self.statistics["error_count"] += 1

    def _add_error(
        self, row_index: int, message: str, row_data: dict[str, Any]
    ) -> None:
        """エラー情報を追加"""
        self.errors.append(
            {
                "row_index": row_index,
                "message": message,
                "data": row_data,
            }
        )

    def _add_warning(
        self, row_index: int, message: str, row_data: dict[str, Any]
    ) -> None:
        """警告情報を追加"""
        self.warnings.append(
            {
                "row_index": row_index,
                "message": message,
                "data": row_data,
            }
        )
        self.statistics["warning_count"] += 1

    def _log_summary(self) -> None:
        """処理結果のサマリーをログ出力"""
        logger.info(
            f"パース完了 - "
            f"合計: {self.statistics['total_rows']}, "
            f"成功: {self.statistics['success_count']}, "
            f"エラー: {self.statistics['error_count']}, "
            f"警告: {self.statistics['warning_count']}"
        )

        # エラーサンプルの出力
        if self.errors:
            logger.warning(f"エラー件数: {len(self.errors)}")
            for error in self.errors[:5]:  # 最初の5件
                logger.warning(f"  行{error['row_index']}: {error['message']}")
