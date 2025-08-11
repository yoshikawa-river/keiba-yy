from typing import Any, ClassVar

"""
バッチプロセッサー

大量データの効率的な処理を行うバッチ処理機能
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.core.database import db_manager
from src.core.exceptions import DataImportError
from src.core.logging import logger
from src.data.importers import BaseCSVParser, CSVFile, CSVFileDetector, FileType
from src.data.importers.horse_parser import HorseCSVParser
from src.data.importers.odds_parser import OddsCSVParser
from src.data.importers.race_parser import RaceCSVParser
from src.data.importers.result_parser import ResultCSVParser


@dataclass
class BatchResult:
    """バッチ処理結果"""

    start_time: datetime
    end_time: Optional[datetime] = None
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    total_rows: int = 0
    success_rows: int = 0
    error_rows: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    file_results: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def processing_time(self) -> float:
        """処理時間(秒)"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_rows == 0:
            return 0
        return self.success_rows / self.total_rows

    def add_file_result(self, file_path: str, result: dict[str, Any]):
        """ファイル処理結果を追加"""
        self.file_results[file_path] = result
        self.processed_files += 1

        # 統計情報の更新
        if "total_rows" in result:
            self.total_rows += result["total_rows"]
        if "success_count" in result:
            self.success_rows += result["success_count"]
        if "error_count" in result:
            self.error_rows += result["error_count"]
        if "errors" in result:
            self.errors.extend(result["errors"])
        if "warnings" in result:
            self.warnings.extend(result["warnings"])

    def add_error(self, file_path: str, error: str):
        """エラーを追加"""
        self.failed_files += 1
        self.errors.append(
            {"file": file_path, "error": error, "timestamp": datetime.now()}
        )


class BatchProcessor:
    """バッチプロセッサー"""

    # ファイルタイプとパーサーのマッピング
    PARSER_MAPPING: ClassVar[dict[FileType, type[BaseCSVParser]]] = {
        FileType.RACE_INFO: RaceCSVParser,
        FileType.HORSE_INFO: HorseCSVParser,
        FileType.RACE_RESULT: ResultCSVParser,
        FileType.ODDS_INFO: OddsCSVParser,
    }

    def __init__(
        self,
        import_dir: Path,
        batch_size: int = 1000,
        parallel: bool = False,
        validate: bool = True,
        dry_run: bool = False,
    ):
        """
        バッチプロセッサーの初期化

        Args:
            import_dir: インポート対象ディレクトリ
            batch_size: バッチサイズ
            parallel: 並列処理を行うか
            validate: バリデーションを行うか
            dry_run: ドライラン(実際の保存は行わない)
        """
        self.import_dir = import_dir
        self.batch_size = batch_size
        self.parallel = parallel
        self.validate = validate
        self.dry_run = dry_run
        self.file_detector = CSVFileDetector(import_dir)

    def process_all(
        self,
        file_types: Optional[list[FileType]] = None,
        file_pattern: str = "*.csv",
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> BatchResult:
        """
        すべてのCSVファイルを処理

        Args:
            file_types: 処理対象のファイルタイプ(Noneの場合はすべて)
            file_pattern: ファイルパターン
            progress_callback: 進捗コールバック関数

        Returns:
            バッチ処理結果
        """
        result = BatchResult(start_time=datetime.now())

        try:
            # CSVファイルを検出
            logger.info(f"CSVファイル検出開始: {self.import_dir}")
            csv_files = self.file_detector.detect_files(pattern=file_pattern)

            # ファイルタイプでフィルタリング
            if file_types:
                csv_files = [f for f in csv_files if f.file_type in file_types]

            result.total_files = len(csv_files)
            logger.info(f"検出されたファイル数: {result.total_files}")

            # ファイルタイプ別にグループ化
            files_by_type = self._group_files_by_type(csv_files)

            # 処理順序を決定(依存関係を考慮)
            processing_order = [
                FileType.RACE_INFO,  # レース情報を最初に
                FileType.HORSE_INFO,  # 馬情報
                FileType.RACE_RESULT,  # レース結果
                FileType.ODDS_INFO,  # オッズ情報
            ]

            # 各タイプごとに処理
            for file_type in processing_order:
                if file_type not in files_by_type:
                    continue

                type_files = files_by_type[file_type]
                logger.info(
                    f"{file_type.value} ファイルの処理開始: {len(type_files)}件"
                )

                for i, csv_file in enumerate(type_files):
                    # 進捗コールバック
                    if progress_callback:
                        progress_callback(
                            result.processed_files + 1, result.total_files
                        )

                    # ファイル処理
                    try:
                        file_result = self._process_file(csv_file)
                        result.add_file_result(str(csv_file.path), file_result)

                        logger.info(
                            f"処理完了: {csv_file.path.name} "
                            f"(成功: {file_result.get('success_count', 0)}, "
                            f"エラー: {file_result.get('error_count', 0)})"
                        )

                    except Exception as e:
                        logger.error(f"ファイル処理エラー: {csv_file.path.name} - {e}")
                        result.add_error(str(csv_file.path), str(e))

            # 処理完了
            result.end_time = datetime.now()

            # サマリーログ
            logger.info(
                f"バッチ処理完了: "
                f"処理時間: {result.processing_time:.1f}秒, "
                f"ファイル: {result.processed_files}/{result.total_files}, "
                f"行: {result.success_rows}/{result.total_rows} "
                f"(成功率: {result.success_rate:.1%})"
            )

        except Exception as e:
            logger.error(f"バッチ処理エラー: {e}")
            result.end_time = datetime.now()
            raise DataImportError(f"バッチ処理に失敗しました: {e}") from e

        return result

    def process_file_type(
        self, file_type: FileType, file_pattern: str = "*.csv"
    ) -> BatchResult:
        """
        特定のファイルタイプのみを処理

        Args:
            file_type: 処理対象のファイルタイプ
            file_pattern: ファイルパターン

        Returns:
            バッチ処理結果
        """
        return self.process_all(file_types=[file_type], file_pattern=file_pattern)

    def _group_files_by_type(
        self, csv_files: list[CSVFile]
    ) -> dict[FileType, list[CSVFile]]:
        """ファイルをタイプ別にグループ化"""
        grouped: dict[FileType, list[CSVFile]] = {}
        for csv_file in csv_files:
            if csv_file.file_type not in grouped:
                grouped[csv_file.file_type] = []
            grouped[csv_file.file_type].append(csv_file)
        return grouped

    def _process_file(self, csv_file: CSVFile) -> dict[str, Any]:
        """
        単一ファイルを処理

        Args:
            csv_file: CSVファイル情報

        Returns:
            処理結果
        """
        # パーサーを取得
        parser_class = self.PARSER_MAPPING.get(csv_file.file_type)
        if not parser_class:
            raise DataImportError(f"未対応のファイルタイプ: {csv_file.file_type}")

        # データベースセッションを作成
        with db_manager.get_session() as session:
            # パーサーインスタンスを作成
            parser = parser_class(session)

            # ドライランモードの設定
            if self.dry_run:
                # トランザクションを開始するが、最後にロールバック
                session.begin()

            try:
                # ファイル処理
                result = parser.parse_file(csv_file, batch_size=self.batch_size)

                if self.dry_run:
                    # ドライランの場合はロールバック
                    session.rollback()
                    logger.info(
                        f"ドライラン: {csv_file.path.name} の変更をロールバック"
                    )
                else:
                    # 実際の処理の場合はコミット
                    session.commit()

                return result  # type: ignore

            except Exception:
                session.rollback()
                raise

    def validate_data_quality(self, csv_files: list[CSVFile]) -> dict[str, Any]:
        """
        データ品質を検証

        Args:
            csv_files: 検証対象のCSVファイルリスト

        Returns:
            品質検証結果
        """
        quality_report = {
            "total_files": len(csv_files),
            "file_quality": {},
            "overall_score": 0,
            "issues": [],
        }

        total_score = 0

        for csv_file in csv_files:
            file_score = 0
            file_issues = []

            # ファイルサイズチェック
            if csv_file.file_size_mb > 100:
                file_issues.append(
                    f"ファイルサイズが大きすぎます: {csv_file.file_size_mb:.1f}MB"
                )
            elif csv_file.file_size_mb < 0.001:
                file_issues.append(
                    f"ファイルが空の可能性があります: {csv_file.file_size_mb:.3f}MB"
                )
            else:
                file_score += 25

            # エンコーディングチェック
            if csv_file.encoding.lower() not in ["utf-8", "shift_jis", "cp932"]:
                file_issues.append(f"非標準のエンコーディング: {csv_file.encoding}")
            else:
                file_score += 25

            # ヘッダーチェック
            if not csv_file.headers:
                file_issues.append("ヘッダーが検出されませんでした")
            elif len(csv_file.headers) < 3:
                file_issues.append(f"カラム数が少なすぎます: {len(csv_file.headers)}")
            else:
                file_score += 25

            # 行数チェック
            if csv_file.row_count == 0:
                file_issues.append("データ行がありません")
            elif csv_file.row_count > 1000000:
                file_issues.append(f"行数が多すぎます: {csv_file.row_count:,}")
            else:
                file_score += 25

            # ファイル品質の記録
            quality_report["file_quality"][str(csv_file.path)] = {
                "score": file_score,
                "issues": file_issues,
                "file_type": csv_file.file_type.value,
                "encoding": csv_file.encoding,
                "row_count": csv_file.row_count,
            }

            quality_report["issues"].extend(  # type: ignore
                [{"file": str(csv_file.path), "issue": issue} for issue in file_issues]
            )

            total_score += file_score

        # 全体スコアの計算
        if csv_files:
            quality_report["overall_score"] = total_score / len(csv_files)

        return quality_report
