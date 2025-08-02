"""
インポートマネージャー

CSVインポート処理の管理とスケジューリング
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.core.logging import logger
from src.data.importers import FileType
from src.data.processors.batch_processor import BatchProcessor, BatchResult


class ImportManager:
    """インポート処理マネージャー"""

    def __init__(self, import_base_dir: Optional[Path] = None):
        """
        インポートマネージャーの初期化

        Args:
            import_base_dir: インポート基底ディレクトリ
        """
        self.import_base_dir = import_base_dir or (settings.DATA_DIR or Path("data")) / "imports"
        self.history_file = (settings.DATA_DIR or Path("data")) / "import_history.json"
        self.import_history = self._load_history()

    def import_from_directory(
        self,
        directory_name: str,
        file_types: Optional[List[FileType]] = None,
        batch_size: int = 1000,
        validate: bool = True,
        dry_run: bool = False,
    ) -> BatchResult:
        """
        指定ディレクトリからインポート

        Args:
            directory_name: ディレクトリ名
            file_types: インポート対象のファイルタイプ
            batch_size: バッチサイズ
            validate: バリデーションを行うか
            dry_run: ドライラン

        Returns:
            バッチ処理結果
        """
        import_dir = self.import_base_dir / directory_name

        if not import_dir.exists():
            raise FileNotFoundError(
                f"インポートディレクトリが存在しません: {import_dir}"
            )

        logger.info(f"インポート開始: {import_dir}")

        # バッチプロセッサーを作成
        processor = BatchProcessor(
            import_dir=import_dir,
            batch_size=batch_size,
            validate=validate,
            dry_run=dry_run,
        )

        # データ品質チェック
        if validate:
            logger.info("データ品質チェック実行中...")
            csv_files = processor.file_detector.detect_files()
            quality_report = processor.validate_data_quality(csv_files)

            if quality_report["overall_score"] < 50:
                logger.warning(
                    f"データ品質スコアが低いです: {quality_report['overall_score']:.1f}/100"
                )

                # 品質問題のサマリー
                for issue in quality_report["issues"][:10]:  # 最初の10件
                    logger.warning(f"品質問題: {issue['file']} - {issue['issue']}")

        # インポート実行
        result = processor.process_all(
            file_types=file_types, progress_callback=self._progress_callback
        )

        # 履歴に記録
        if not dry_run:
            self._record_import(directory_name, result)

        return result

    def import_incremental(
        self,
        directory_name: str,
        since: Optional[datetime] = None,
        file_types: Optional[List[FileType]] = None,
    ) -> BatchResult:
        """
        増分インポート（前回インポート以降の新規ファイルのみ）

        Args:
            directory_name: ディレクトリ名
            since: この日時以降のファイルをインポート（Noneの場合は前回インポート日時）
            file_types: インポート対象のファイルタイプ

        Returns:
            バッチ処理結果
        """
        import_dir = self.import_base_dir / directory_name

        # 前回インポート日時を取得
        if since is None:
            last_import = self._get_last_import(directory_name)
            if last_import:
                since = datetime.fromisoformat(last_import["timestamp"])
            else:
                logger.warning(f"前回のインポート履歴がありません: {directory_name}")
                since = datetime.min

        logger.info(f"増分インポート開始: {import_dir} (since: {since})")

        # バッチプロセッサーを作成
        processor = BatchProcessor(import_dir=import_dir)

        # ファイルをフィルタリング
        csv_files = processor.file_detector.detect_files()
        filtered_files = []

        for csv_file in csv_files:
            # ファイルの更新日時をチェック
            file_mtime = datetime.fromtimestamp(csv_file.path.stat().st_mtime)
            if file_mtime > since:
                filtered_files.append(csv_file)

        logger.info(f"新規/更新ファイル数: {len(filtered_files)}/{len(csv_files)}")

        if not filtered_files:
            logger.info("処理対象のファイルがありません")
            return BatchResult(start_time=datetime.now(), end_time=datetime.now())

        # フィルタリングされたファイルのみを処理
        # TODO: BatchProcessorに特定ファイルのみを処理する機能を追加
        result = processor.process_all(file_types=file_types)

        # 履歴に記録
        self._record_import(directory_name, result, incremental=True)

        return result

    def retry_failed_imports(self, directory_name: Optional[str] = None) -> BatchResult:
        """
        失敗したインポートをリトライ

        Args:
            directory_name: 特定のディレクトリのみリトライ（Noneの場合はすべて）

        Returns:
            バッチ処理結果
        """
        # 失敗したインポートを検索
        failed_imports = []

        for dir_name, imports in self.import_history.items():
            if directory_name and dir_name != directory_name:
                continue

            for import_record in imports:
                if import_record.get("failed_files", 0) > 0:
                    failed_imports.append(
                        {
                            "directory": dir_name,
                            "timestamp": import_record["timestamp"],
                            "failed_files": import_record["failed_files"],
                        }
                    )

        if not failed_imports:
            logger.info("リトライ対象のインポートがありません")
            return BatchResult(start_time=datetime.now(), end_time=datetime.now())

        logger.info(f"リトライ対象: {len(failed_imports)}件")

        # TODO: 失敗したファイルのみをリトライする実装
        # 現在は単純に全体を再実行
        total_result = BatchResult(start_time=datetime.now())

        for failed_import in failed_imports:
            logger.info(f"リトライ: {failed_import['directory']}")
            result = self.import_from_directory(failed_import["directory"])

            # 結果をマージ
            total_result.total_files += result.total_files
            total_result.processed_files += result.processed_files
            total_result.failed_files += result.failed_files
            total_result.total_rows += result.total_rows
            total_result.success_rows += result.success_rows
            total_result.error_rows += result.error_rows

        total_result.end_time = datetime.now()
        return total_result

    def get_import_status(self, directory_name: Optional[str] = None) -> Dict[str, Any]:
        """
        インポート状況を取得

        Args:
            directory_name: 特定のディレクトリの状況（Noneの場合はすべて）

        Returns:
            インポート状況
        """
        if directory_name:
            imports = self.import_history.get(directory_name, [])
            return {
                "directory": directory_name,
                "total_imports": len(imports),
                "last_import": imports[-1] if imports else None,
                "success_rate": self._calculate_success_rate(imports),
                "total_files_processed": sum(
                    imp.get("processed_files", 0) for imp in imports
                ),
                "total_rows_processed": sum(
                    imp.get("total_rows", 0) for imp in imports
                ),
            }
        else:
            # 全体の状況
            status = {
                "directories": {},
                "total_imports": 0,
                "total_files_processed": 0,
                "total_rows_processed": 0,
            }

            for dir_name, imports in self.import_history.items():
                status["directories"][dir_name] = {  # type: ignore
                    "total_imports": len(imports),
                    "last_import": imports[-1] if imports else None,
                    "success_rate": self._calculate_success_rate(imports),
                }
                status["total_imports"] += len(imports)  # type: ignore
                status["total_files_processed"] += sum(
                    imp.get("processed_files", 0) for imp in imports
                )
                status["total_rows_processed"] += sum(
                    imp.get("total_rows", 0) for imp in imports
                )

            return status

    def _progress_callback(self, current: int, total: int):
        """進捗コールバック"""
        percentage = (current / total * 100) if total > 0 else 0
        logger.info(f"進捗: {current}/{total} ({percentage:.1f}%)")

    def _load_history(self) -> Dict[str, List[Dict[str, Any]]]:
        """インポート履歴を読み込み"""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r") as f:
                    return json.load(f)  # type: ignore
            except Exception as e:
                logger.error(f"履歴ファイル読み込みエラー: {e}")
        return {}

    def _save_history(self):
        """インポート履歴を保存"""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, "w") as f:
                json.dump(self.import_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"履歴ファイル保存エラー: {e}")

    def _record_import(
        self, directory_name: str, result: BatchResult, incremental: bool = False
    ):
        """インポート履歴を記録"""
        if directory_name not in self.import_history:
            self.import_history[directory_name] = []

        record = {
            "timestamp": datetime.now().isoformat(),
            "incremental": incremental,
            "total_files": result.total_files,
            "processed_files": result.processed_files,
            "failed_files": result.failed_files,
            "total_rows": result.total_rows,
            "success_rows": result.success_rows,
            "error_rows": result.error_rows,
            "processing_time": result.processing_time,
            "success_rate": result.success_rate,
        }

        self.import_history[directory_name].append(record)
        self._save_history()

    def _get_last_import(self, directory_name: str) -> Optional[Dict[str, Any]]:
        """最後のインポート情報を取得"""
        imports = self.import_history.get(directory_name, [])
        return imports[-1] if imports else None

    def _calculate_success_rate(self, imports: List[Dict[str, Any]]) -> float:
        """成功率を計算"""
        if not imports:
            return 0

        total_rows = sum(imp.get("total_rows", 0) for imp in imports)
        success_rows = sum(imp.get("success_rows", 0) for imp in imports)

        return success_rows / total_rows if total_rows > 0 else 0  # type: ignore
