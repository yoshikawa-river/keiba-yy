"""
バッチプロセッサーのユニットテスト
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.data.importers import CSVFile, FileType
from src.data.processors import BatchProcessor, BatchResult
from src.data.models.race import Race


class TestBatchResult:
    """BatchResultのテスト"""

    def test_processing_time(self):
        """処理時間計算のテスト"""
        result = BatchResult(start_time=datetime(2024, 1, 1, 12, 0, 0))
        result.end_time = datetime(2024, 1, 1, 12, 0, 30)

        assert result.processing_time == 30.0

    def test_success_rate(self):
        """成功率計算のテスト"""
        result = BatchResult(start_time=datetime.now())
        result.total_rows = 100
        result.success_rows = 75

        assert result.success_rate == 0.75

    def test_success_rate_zero_rows(self):
        """行数0の場合の成功率"""
        result = BatchResult(start_time=datetime.now())
        result.total_rows = 0

        assert result.success_rate == 0

    def test_add_file_result(self):
        """ファイル結果追加のテスト"""
        result = BatchResult(start_time=datetime.now())

        file_result = {
            "total_rows": 100,
            "success_count": 90,
            "error_count": 10,
            "errors": [{"error": "test error"}],
            "warnings": [{"warning": "test warning"}],
        }

        result.add_file_result("test.csv", file_result)

        assert result.processed_files == 1
        assert result.total_rows == 100
        assert result.success_rows == 90
        assert result.error_rows == 10
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert "test.csv" in result.file_results

    def test_add_error(self):
        """エラー追加のテスト"""
        result = BatchResult(start_time=datetime.now())

        result.add_error("test.csv", "Test error message")

        assert result.failed_files == 1
        assert len(result.errors) == 1
        assert result.errors[0]["file"] == "test.csv"
        assert result.errors[0]["error"] == "Test error message"


class TestBatchProcessor:
    """BatchProcessorのテスト"""

    @pytest.fixture
    def mock_import_dir(self, tmp_path):
        """テスト用インポートディレクトリ"""
        import_dir = tmp_path / "imports"
        import_dir.mkdir()
        return import_dir

    @pytest.fixture
    def processor(self, mock_import_dir):
        """テスト用プロセッサー"""
        return BatchProcessor(
            import_dir=mock_import_dir, batch_size=100, validate=True, dry_run=False
        )

    @pytest.fixture
    def mock_csv_files(self, mock_import_dir):
        """モックCSVファイル"""
        # 実際のファイルを作成
        race_file = mock_import_dir / "races.csv"
        with open(race_file, "w", encoding="utf-8") as f:
            f.write("レースID,開催日,R,レース名,競馬場,コース,距離\n")
            f.write("202401010101,2024-01-01,1,テストレース,東京,ダート,1200\n")

        horse_file = mock_import_dir / "horses.csv"
        with open(horse_file, "w", encoding="utf-8") as f:
            f.write("馬ID,馬名,性齢\n")
            f.write("20210001,テスト馬,牝3\n")

        return [
            CSVFile(
                path=race_file,
                file_type=FileType.RACE_INFO,
                encoding="utf-8",
                delimiter=",",
                headers=[
                    "レースID",
                    "開催日",
                    "R",
                    "レース名",
                    "競馬場",
                    "コース",
                    "距離",
                ],
                row_count=1,
                file_size=race_file.stat().st_size,
            ),
            CSVFile(
                path=horse_file,
                file_type=FileType.HORSE_INFO,
                encoding="utf-8",
                delimiter=",",
                headers=["馬ID", "馬名", "性齢"],
                row_count=1,
                file_size=horse_file.stat().st_size,
            ),
        ]

    def test_group_files_by_type(self, processor, mock_csv_files):
        """ファイルタイプ別グループ化のテスト"""
        grouped = processor._group_files_by_type(mock_csv_files)

        assert FileType.RACE_INFO in grouped
        assert FileType.HORSE_INFO in grouped
        assert len(grouped[FileType.RACE_INFO]) == 1
        assert len(grouped[FileType.HORSE_INFO]) == 1

    @patch("src.data.processors.batch_processor.db_manager")
    def test_process_file(self, mock_db_manager, processor, mock_csv_files):
        """ファイル処理のテスト"""
        # モックセッションを設定
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        # レースのクエリ結果をモック
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        # CSVファイルが正しく作成されていることを確認
        assert mock_csv_files[0].path.exists()

        # ファイル処理実行
        result = processor._process_file(mock_csv_files[0])

        # 結果の確認
        assert "statistics" in result
        stats = result["statistics"]
        assert "total_rows" in stats
        assert "success_count" in stats
        assert "error_count" in stats
        assert stats["total_rows"] == 1  # 実際のデータ行数
        assert stats["success_count"] == 1
        assert stats["error_count"] == 0

    @patch("src.data.processors.batch_processor.db_manager")
    def test_process_file_dry_run(self, mock_db_manager, processor, mock_csv_files):
        """ドライラン時のファイル処理テスト"""
        processor.dry_run = True

        # モックセッションを設定
        mock_session = MagicMock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session

        # レースのクエリ結果をモック
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        # ファイル処理実行
        result = processor._process_file(mock_csv_files[0])

        # ドライランではロールバックが呼ばれる
        assert mock_session.rollback.called
        # 注意: parse_fileメソッドでコミットされるが、その後ドライランでロールバックされる

        # 結果の確認
        assert "statistics" in result
        stats = result["statistics"]
        assert stats["total_rows"] == 1  # 実際のデータ行数

    def test_validate_data_quality(self, processor, mock_csv_files):
        """データ品質検証のテスト"""
        quality_report = processor.validate_data_quality(mock_csv_files)

        assert quality_report["total_files"] == 2
        assert "file_quality" in quality_report
        assert quality_report["overall_score"] > 0

        # 各ファイルの品質チェック
        for csv_file in mock_csv_files:
            file_path = str(csv_file.path)
            assert file_path in quality_report["file_quality"]
            file_quality = quality_report["file_quality"][file_path]
            assert "score" in file_quality
            assert "issues" in file_quality

    def test_validate_data_quality_large_file(self, processor, mock_import_dir):
        """大きいファイルの品質検証"""
        large_file = CSVFile(
            path=mock_import_dir / "large.csv",
            file_type=FileType.RACE_INFO,
            encoding="utf-8",
            delimiter=",",
            headers=["col1", "col2"],
            row_count=2000000,  # 200万行
            file_size=150 * 1024 * 1024,  # 150MB
        )

        quality_report = processor.validate_data_quality([large_file])

        # 大きいファイルの問題が検出される
        assert len(quality_report["issues"]) > 0
        assert any(
            "ファイルサイズが大きすぎます" in issue["issue"]
            for issue in quality_report["issues"]
        )
        assert any(
            "行数が多すぎます" in issue["issue"] for issue in quality_report["issues"]
        )

    def test_validate_data_quality_empty_file(self, processor, mock_import_dir):
        """空ファイルの品質検証"""
        empty_file = CSVFile(
            path=mock_import_dir / "empty.csv",
            file_type=FileType.RACE_INFO,
            encoding="utf-8",
            delimiter=",",
            headers=[],
            row_count=0,
            file_size=0,
        )

        quality_report = processor.validate_data_quality([empty_file])

        # 空ファイルの問題が検出される
        assert len(quality_report["issues"]) > 0
        assert any(
            "ファイルが空の可能性" in issue["issue"]
            for issue in quality_report["issues"]
        )
        assert any(
            "ヘッダーが検出されませんでした" in issue["issue"]
            for issue in quality_report["issues"]
        )

    @patch.object(BatchProcessor, "_process_file")
    def test_process_all(self, mock_process_file, processor, mock_csv_files):
        """全ファイル処理のテスト"""
        # ファイル検出のモック
        with patch.object(
            processor.file_detector, "detect_files", return_value=mock_csv_files
        ):
            # ファイル処理のモック
            mock_process_file.return_value = {
                "total_rows": 100,
                "success_count": 95,
                "error_count": 5,
                "errors": [],
                "warnings": [],
            }

            # 処理実行
            result = processor.process_all()

            assert result.total_files == 2
            assert result.processed_files == 2
            assert result.total_rows == 200  # 100 * 2
            assert result.success_rows == 190  # 95 * 2
            assert mock_process_file.call_count == 2

    @patch.object(BatchProcessor, "_process_file")
    def test_process_all_with_file_type_filter(
        self, mock_process_file, processor, mock_csv_files
    ):
        """ファイルタイプフィルター付き処理のテスト"""
        with patch.object(
            processor.file_detector, "detect_files", return_value=mock_csv_files
        ):
            mock_process_file.return_value = {
                "total_rows": 100,
                "success_count": 95,
                "error_count": 5,
                "errors": [],
                "warnings": [],
            }

            # レース情報のみ処理
            processor.process_all(file_types=[FileType.RACE_INFO])

            # 1ファイルのみ処理される
            assert mock_process_file.call_count == 1

    @patch.object(BatchProcessor, "_process_file")
    def test_process_all_with_progress_callback(
        self, mock_process_file, processor, mock_csv_files
    ):
        """進捗コールバック付き処理のテスト"""
        with patch.object(
            processor.file_detector, "detect_files", return_value=mock_csv_files
        ):
            mock_process_file.return_value = {
                "total_rows": 100,
                "success_count": 95,
                "error_count": 5,
                "errors": [],
                "warnings": [],
            }

            # 進捗記録用
            progress_calls = []

            def progress_callback(current, total):
                progress_calls.append((current, total))

            # 処理実行
            processor.process_all(progress_callback=progress_callback)

            # 進捗コールバックが呼ばれる
            assert len(progress_calls) == 2
            assert progress_calls[0] == (1, 2)
            assert progress_calls[1] == (2, 2)

    @patch.object(BatchProcessor, "_process_file")
    def test_process_file_type(self, mock_process_file, processor, mock_csv_files):
        """特定ファイルタイプ処理のテスト"""
        with patch.object(
            processor.file_detector, "detect_files", return_value=mock_csv_files
        ):
            mock_process_file.return_value = {
                "total_rows": 100,
                "success_count": 95,
                "error_count": 5,
                "errors": [],
                "warnings": [],
            }

            # 馬情報のみ処理
            processor.process_file_type(FileType.HORSE_INFO)

            # 1ファイルのみ処理される
            assert mock_process_file.call_count == 1
