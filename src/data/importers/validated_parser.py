"""
バリデーション統合パーサー

バリデーション機能を統合したCSVパーサー
"""

from typing import Any, Dict, List, Optional, Type

import pandas as pd
from sqlalchemy.orm import Session

from src.core.logging import logger
from src.data.importers.base_parser import BaseCSVParser
from src.data.validators import DataValidator, SchemaValidator, ValidationResult
from src.data.validators.schema_validator import Schema


class ValidatedCSVParser(BaseCSVParser):
    """バリデーション機能を統合したCSVパーサー"""

    def __init__(
        self,
        db_session: Session,
        schema: Optional[Schema] = None,
        validate_business_logic: bool = True,
    ):
        """
        バリデーション統合パーサーの初期化

        Args:
            db_session: データベースセッション
            schema: スキーマ定義（指定しない場合は自動選択）
            validate_business_logic: ビジネスロジック検証を行うか
        """
        super().__init__(db_session)
        self.schema = schema
        self.validate_business_logic = validate_business_logic

        # バリデーターの初期化
        if self.schema:
            self.schema_validator: Optional[SchemaValidator] = SchemaValidator(
                self.schema
            )
        else:
            self.schema_validator: Optional[SchemaValidator] = None

        if self.validate_business_logic:
            self.data_validator: Optional[DataValidator] = DataValidator(db_session)
        else:
            self.data_validator: Optional[DataValidator] = None

    def _validate_row_with_validators(
        self, row_data: Dict[str, Any]
    ) -> ValidationResult:
        """
        バリデーターを使用して行データを検証

        Args:
            row_data: 検証対象データ

        Returns:
            バリデーション結果
        """
        # 統合結果
        combined_result = ValidationResult(is_valid=True)

        # スキーマバリデーション
        if self.schema_validator:
            schema_result = self.schema_validator.validate(row_data)
            combined_result.merge(schema_result)

        # ビジネスロジックバリデーション
        if self.data_validator and combined_result.is_valid:
            business_result = self.data_validator.validate(row_data)
            combined_result.merge(business_result)

        return combined_result

    def _process_batch(
        self, batch_df: pd.DataFrame, dry_run: bool = False
    ) -> None:
        """
        バッチデータを処理（バリデーション統合版）

        Args:
            batch_df: バッチデータフレーム

        Returns:
            処理結果統計
        """
        success = 0
        error = 0
        skip = 0

        for idx, row in batch_df.iterrows():
            try:
                # 行データを辞書に変換
                row_dict = row.to_dict()

                # データ変換
                try:
                    transformed = self._transform_row(row_dict)
                except Exception as e:
                    logger.error(f"行 {idx}: 変換エラー - {e}")
                    self._add_error(idx, str(e), row_dict)
                    error += 1
                    continue

                # バリデーション実行
                validation_result = self._validate_row_with_validators(transformed)

                # バリデーション結果の処理
                if not validation_result.is_valid:
                    # エラーログ
                    for val_error in validation_result.errors:
                        logger.error(
                            f"行 {idx}: バリデーションエラー - "
                            f"フィールド: {val_error.field}, "
                            f"メッセージ: {val_error.message}"
                        )
                        self._add_error(
                            idx,
                            val_error.message,
                            {val_error.field: val_error.value},
                        )
                    error += 1
                    continue

                # 警告ログ
                for warning in validation_result.warnings:
                    logger.warning(f"行 {idx}: {warning}")
                    self._add_warning(idx, warning, row_dict)

                # 従来のバリデーション（互換性のため）
                is_valid, error_msg = self._validate_row(transformed)
                if not is_valid:
                    logger.error(f"行 {idx}: {error_msg}")
                    self._add_error(
                        idx, error_msg or "バリデーションエラー", row_dict
                    )
                    error += 1
                    continue

                # データ保存
                saved = self._save_row(transformed)
                if saved:
                    success += 1
                else:
                    skip += 1

            except Exception as e:
                logger.error(f"行 {idx}: 予期しないエラー - {e}")
                self._add_error(idx, f"予期しないエラー: {str(e)}", row_dict)
                error += 1

        # 統計情報の更新
        self.statistics["success_count"] += success
        self.statistics["error_count"] += error
        self.statistics["skip_count"] += skip

        return {"success": success, "error": error, "skip": skip}

    def get_validation_report(self) -> Dict[str, Any]:
        """
        バリデーションレポートを取得

        Returns:
            バリデーションレポート
        """
        report = {
            "statistics": self.statistics,
            "errors": self.errors,
            "warnings": self.warnings,
            "validation_summary": {
                "total_errors": len(self.errors),
                "total_warnings": len(self.warnings),
                "error_types": self._count_error_types(),
                "warning_types": self._count_warning_types(),
            },
        }

        # エラー率の計算
        if self.statistics["total_rows"] > 0:
            total_rows = self.statistics["total_rows"]
            report["validation_summary"]["error_rate"] = (
                self.statistics["error_count"] / total_rows * 100
            )
            report["validation_summary"]["success_rate"] = (
                self.statistics["success_count"] / total_rows * 100
            )

        return report

    def _count_error_types(self) -> Dict[str, int]:
        """エラータイプをカウント"""
        error_types: Dict[str, int] = {}
        for error in self.errors:
            error_type = error.get("type", "unknown")
            error_types[error_type] = error_types.get(error_type, 0) + 1
        return error_types

    def _count_warning_types(self) -> Dict[str, int]:
        """警告タイプをカウント"""
        warning_types: Dict[str, int] = {}
        for warning in self.warnings:
            warning_type = warning.get("type", "unknown")
            warning_types[warning_type] = warning_types.get(warning_type, 0) + 1
        return warning_types
