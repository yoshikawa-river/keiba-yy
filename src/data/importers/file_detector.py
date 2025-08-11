"""
CSVファイル検出・分類機能

TARGET frontier JVから出力されたCSVファイルを検出し、
ファイルタイプを自動判定する機能を提供
"""

import csv
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Tuple

import chardet

from src.core.logging import logger


class FileType(Enum):
    """CSVファイルタイプ"""

    RACE_INFO = "race_info"
    HORSE_INFO = "horse_info"
    RACE_RESULT = "race_result"
    ODDS_INFO = "odds_info"
    TRAINING_DATA = "training_data"
    UNKNOWN = "unknown"


@dataclass
class CSVFile:
    """CSVファイル情報"""

    path: Path
    file_type: FileType
    encoding: str
    delimiter: str
    headers: List[str]
    row_count: int
    file_size: int  # バイト単位

    @property
    def file_size_mb(self) -> float:
        """ファイルサイズをMB単位で取得"""
        return self.file_size / (1024 * 1024)


class CSVFileDetector:
    """CSVファイル検出・分類クラス"""

    def __init__(self, import_dir: Path):
        """
        CSVファイル検出器の初期化

        Args:
            import_dir: インポート対象ディレクトリ
        """
        self.import_dir = import_dir
        self.type_patterns = self._initialize_type_patterns()

    def _initialize_type_patterns(self) -> Dict[FileType, List[str]]:
        """ファイルタイプ判定用のパターンを初期化"""
        return {
            FileType.RACE_INFO: ["レース名", "開催日", "競馬場", "距離", "レース番号"],
            FileType.HORSE_INFO: ["馬名", "性別", "生年月日", "父", "母", "馬主"],
            FileType.RACE_RESULT: ["着順", "馬名", "タイム", "オッズ", "馬番"],
            FileType.ODDS_INFO: ["馬番", "単勝", "複勝", "馬連", "馬単"],
            FileType.TRAINING_DATA: ["調教日", "調教内容", "タイム", "調教師"],
        }

    def detect_files(self, pattern: str = "*.csv") -> List[CSVFile]:
        """
        CSVファイルを検出して分類

        Args:
            pattern: ファイル検索パターン

        Returns:
            検出されたCSVファイルのリスト
        """
        csv_files: List[CSVFile] = []

        if not self.import_dir.exists():
            logger.warning(f"インポートディレクトリが存在しません: {self.import_dir}")
            return csv_files

        for file_path in self.import_dir.glob(pattern):
            if not file_path.is_file():
                continue

            try:
                csv_file = self._analyze_file(file_path)
                csv_files.append(csv_file)
                logger.info(
                    f"検出: {file_path.name} - "
                    f"タイプ: {csv_file.file_type.value} - "
                    f"サイズ: {csv_file.file_size_mb:.2f}MB"
                )
            except Exception as e:
                logger.error(f"ファイル解析エラー: {file_path.name} - {e}")

        logger.info(f"合計 {len(csv_files)} ファイルを検出")
        return csv_files

    def _analyze_file(self, file_path: Path) -> CSVFile:
        """
        ファイルを解析して情報を取得

        Args:
            file_path: 解析対象ファイルパス

        Returns:
            CSVファイル情報
        """
        # ファイルサイズ取得
        file_size = file_path.stat().st_size

        # 文字コード検出
        encoding = self._detect_encoding(file_path)

        # ヘッダーとデリミタ検出
        headers, delimiter = self._detect_headers(file_path, encoding)

        # ファイルタイプ判定
        file_type = self._detect_file_type(headers)

        # 行数カウント
        row_count = self._count_rows(file_path, encoding)

        return CSVFile(
            path=file_path,
            file_type=file_type,
            encoding=encoding,
            delimiter=delimiter,
            headers=headers,
            row_count=row_count,
            file_size=file_size,
        )

    def _detect_encoding(self, file_path: Path) -> str:
        """
        文字コードを検出

        Args:
            file_path: 対象ファイルパス

        Returns:
            検出された文字コード
        """
        with open(file_path, "rb") as f:
            # 最初の10KBを読み込んで判定
            raw_data = f.read(10240)
            result = chardet.detect(raw_data)

        encoding = (result.get("encoding") or "").lower() if result else ""
        confidence = result.get("confidence", 0) if result else 0

        # 日本語エンコーディングの正規化
        encoding_map = {
            "shift_jis": "shift_jis",
            "shift-jis": "shift_jis",
            "sjis": "shift_jis",
            "cp932": "cp932",
            "utf-8": "utf-8",
            "utf8": "utf-8",
        }

        normalized = encoding_map.get(encoding, encoding)

        # 信頼度が低い場合の処理
        if confidence < 0.8:
            logger.warning(
                f"文字コード検出の信頼度が低い: {file_path.name} "
                f"({encoding} - {confidence:.2%})"
            )
            # 日本の競馬データはshift_jisが多いため、デフォルトとする
            return "shift_jis"

        return normalized

    def _detect_headers(self, file_path: Path, encoding: str) -> Tuple[List[str], str]:
        """
        ヘッダーとデリミタを検出

        Args:
            file_path: 対象ファイルパス
            encoding: 文字コード

        Returns:
            (ヘッダーリスト, デリミタ)
        """
        with open(file_path, encoding=encoding, errors="replace") as f:
            # 最初の1KBを読み込んでデリミタ推測
            sample = f.read(1024)
            f.seek(0)

            # CSV Snifferでデリミタを推測
            try:
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
            except csv.Error:
                # 推測失敗時はカンマをデフォルト
                delimiter = ","

            # ヘッダー読み込み
            reader = csv.reader(f, delimiter=delimiter)
            headers = next(reader, [])

        # ヘッダーの正規化(前後の空白除去)
        headers = [h.strip() for h in headers]

        return headers, delimiter

    def _detect_file_type(self, headers: List[str]) -> FileType:
        """
        ヘッダーからファイルタイプを判定

        Args:
            headers: ヘッダーリスト

        Returns:
            判定されたファイルタイプ
        """
        if not headers:
            return FileType.UNKNOWN

        # 各タイプとのマッチ度を計算
        match_scores = {}

        for file_type, patterns in self.type_patterns.items():
            match_count = 0
            for pattern in patterns:
                # 部分一致でチェック
                if any(pattern in header for header in headers):
                    match_count += 1

            # マッチ率を計算
            match_rate = match_count / len(patterns) if patterns else 0
            match_scores[file_type] = match_rate

        # 最もマッチ率の高いタイプを選択
        best_type = max(match_scores, key=lambda x: match_scores[x])
        best_score = match_scores[best_type]

        # 閾値(70%)以上でないと判定しない
        if best_score >= 0.7:
            return best_type

        return FileType.UNKNOWN

    def _count_rows(self, file_path: Path, encoding: str) -> int:
        """
        行数をカウント(ヘッダー除外)

        Args:
            file_path: 対象ファイルパス
            encoding: 文字コード

        Returns:
            データ行数
        """
        with open(file_path, encoding=encoding, errors="replace") as f:
            # ヘッダーをスキップしてカウント
            row_count = sum(1 for _ in f) - 1

        return max(0, row_count)  # 負の値を防ぐ

    def get_files_by_type(
        self, file_type: FileType, csv_files: Optional[List[CSVFile]] = None
    ) -> List[CSVFile]:
        """
        特定タイプのファイルのみを取得

        Args:
            file_type: 取得したいファイルタイプ
            csv_files: フィルタ対象のファイルリスト(Noneの場合は再検出)

        Returns:
            指定タイプのファイルリスト
        """
        if csv_files is None:
            csv_files = self.detect_files()

        return [f for f in csv_files if f.file_type == file_type]
