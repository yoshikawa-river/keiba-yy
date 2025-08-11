"""JRA-VAN mykeibaDB形式モックデータ生成器

現実的で一貫性のあるテストデータを生成する。
特徴量抽出パイプラインのテストとモデル開発に使用。
"""

import random
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from loguru import logger

from src.data.mock.mock_constants import (
    DEFAULT_END_DATE,
    DEFAULT_START_DATE,
    DISTANCES,
    FAMOUS_RACE_NAMES,
    GRADE_CODES,
    HORSE_NAMES,
    HORSES_PER_RACE_RANGE,
    JOCKEY_NAMES,
    KAISAI_SCHEDULE,
    KEIBAJO_MASTER,
    OWNER_NAMES,
    RACES_PER_DAY_RANGE,
    SIRE_NAMES,
    TRACK_CODES,
    TRAINER_NAMES,
)


class MockDataGenerator:
    """JRA-VAN mykeibaDB形式モックデータ生成器

    現実的で一貫性のあるテストデータを生成する。
    時系列データの蓄積により、特徴量抽出に対応したデータを提供。
    """

    def __init__(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        num_horses: int = 5000,
        num_jockeys: int = 200,
        num_trainers: int = 150,
        random_seed: int = 42,
    ):
        """モックデータ生成器初期化

        Args:
            start_date: データ生成開始日
            end_date: データ生成終了日
            num_horses: 生成する馬の数
            num_jockeys: 生成する騎手の数
            num_trainers: 生成する調教師の数
            random_seed: 乱数シード
        """
        self.start_date = start_date or DEFAULT_START_DATE
        self.end_date = end_date or DEFAULT_END_DATE
        self.num_horses = num_horses
        self.num_jockeys = num_jockeys
        self.num_trainers = num_trainers

        # 乱数シード設定
        random.seed(random_seed)
        np.random.seed(random_seed)

        logger.info(f"モックデータ生成器初期化: {self.start_date} ~ {self.end_date}")
        logger.info(
            f"馬数: {num_horses}, 騎手数: {num_jockeys}, 調教師数: {num_trainers}"
        )

        # マスターデータ格納
        self.horses_master: list[dict] = []
        self.jockeys_master: list[dict] = []
        self.trainers_master: list[dict] = []
        self.owners_master: list[dict] = []

        # レースデータ格納
        self.races_data: list[dict] = []
        self.race_entries_data: list[dict] = []

        # IDカウンター
        self._race_counter = 1
        self._horse_counter = 1
        self._jockey_counter = 1
        self._trainer_counter = 1
        self._owner_counter = 1

    def generate_all_data(self) -> dict[str, pd.DataFrame]:
        """全データを生成してDataFrameとして返す

        Returns:
            各テーブルのDataFrameを含む辞書
        """
        logger.info("全モックデータ生成開始")

        # マスターデータ生成
        self._generate_masters()

        # レースデータ生成
        self._generate_races_and_entries()

        # DataFrameに変換
        dataframes = {
            "horses_master": pd.DataFrame(self.horses_master),
            "jockeys_master": pd.DataFrame(self.jockeys_master),
            "trainers_master": pd.DataFrame(self.trainers_master),
            "owners_master": pd.DataFrame(self.owners_master),
            "races": pd.DataFrame(self.races_data),
            "race_entries": pd.DataFrame(self.race_entries_data),
        }

        logger.info("データ生成完了:")
        for name, df in dataframes.items():
            logger.info(f"  {name}: {len(df):,} 件")

        return dataframes

    def _generate_masters(self):
        """マスターデータを生成"""
        logger.info("マスターデータ生成開始")

        self._generate_horses_master()
        self._generate_jockeys_master()
        self._generate_trainers_master()
        self._generate_owners_master()

    def _generate_horses_master(self):
        """馬マスターデータを生成"""
        logger.info("馬マスター生成開始")

        for i in range(self.num_horses):
            horse_id = f"H{self._horse_counter:06d}"
            birth_date = self.start_date - timedelta(
                days=random.randint(1095, 2190)
            )  # 3-6歳

            # 血統データ生成
            sire = random.choice(SIRE_NAMES)
            dam_sire = random.choice(SIRE_NAMES)

            horse_data = {
                "KETTO_TOROKU_BANGO": horse_id,
                "BAMEI": f"{random.choice(HORSE_NAMES)}{i:03d}",
                "SEINENGAPPI": birth_date.strftime("%Y%m%d"),
                "SEIBETSU_CODE": random.choice(["1", "2"]),  # 1:牡, 2:牝
                "MOSHOKU_CODE": f"{random.randint(1, 15):02d}",  # 毛色
                "KETTO1_BAMEI": sire,  # 父
                "KETTO5_BAMEI": dam_sire,  # 母父
                "TOZAI_SHOZOKU_CODE": random.choice(["1", "2"]),  # 1:関東, 2:関西
                "CHOKYOSHI_CODE": f"T{random.randint(1, self.num_trainers):05d}",
                "INSERT_TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "UPDATE_TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            self.horses_master.append(horse_data)
            self._horse_counter += 1

        logger.info(f"馬マスター生成完了: {len(self.horses_master):,} 頭")

    def _generate_jockeys_master(self):
        """騎手マスターデータを生成"""
        logger.info("騎手マスター生成開始")

        selected_names = random.sample(
            JOCKEY_NAMES, min(self.num_jockeys, len(JOCKEY_NAMES))
        )

        for i, name in enumerate(selected_names):
            jockey_id = f"J{self._jockey_counter:05d}"

            jockey_data = {
                "KISHU_CODE": jockey_id,
                "KISHUMEI": name,
                "KISHUMEI_RYAKUSHO": name[:4],  # 略称
                "SEINENGAPPI": (
                    date(1970, 1, 1) + timedelta(days=random.randint(0, 18250))
                ).strftime("%Y%m%d"),
                "SEIBETSU_CODE": random.choice(["1", "2"]),
                "TOZAI_SHOZOKU_CODE": random.choice(["1", "2"]),
                "INSERT_TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "UPDATE_TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            self.jockeys_master.append(jockey_data)
            self._jockey_counter += 1

        # 残りは生成された名前で補完
        for i in range(len(selected_names), self.num_jockeys):
            jockey_id = f"J{self._jockey_counter:05d}"

            jockey_data = {
                "KISHU_CODE": jockey_id,
                "KISHUMEI": f"騎手{i+1:03d}",
                "KISHUMEI_RYAKUSHO": f"騎{i+1:03d}",
                "SEINENGAPPI": (
                    date(1970, 1, 1) + timedelta(days=random.randint(0, 18250))
                ).strftime("%Y%m%d"),
                "SEIBETSU_CODE": random.choice(["1", "2"]),
                "TOZAI_SHOZOKU_CODE": random.choice(["1", "2"]),
                "INSERT_TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "UPDATE_TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            self.jockeys_master.append(jockey_data)
            self._jockey_counter += 1

        logger.info(f"騎手マスター生成完了: {len(self.jockeys_master):,} 人")

    def _generate_trainers_master(self):
        """調教師マスターデータを生成"""
        logger.info("調教師マスター生成開始")

        selected_names = random.sample(
            TRAINER_NAMES, min(self.num_trainers, len(TRAINER_NAMES))
        )

        for i, name in enumerate(selected_names):
            trainer_id = f"T{self._trainer_counter:05d}"

            trainer_data = {
                "CHOKYOSHI_CODE": trainer_id,
                "CHOKYOSHIMEI": name,
                "CHOKYOSHIMEI_RYAKUSHO": name[:4],
                "SEINENGAPPI": (
                    date(1950, 1, 1) + timedelta(days=random.randint(0, 25550))
                ).strftime("%Y%m%d"),
                "SEIBETSU_CODE": "1",  # ほとんど男性
                "TOZAI_SHOZOKU_CODE": random.choice(["1", "2"]),
                "INSERT_TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "UPDATE_TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            self.trainers_master.append(trainer_data)
            self._trainer_counter += 1

        # 残りは生成された名前で補完
        for i in range(len(selected_names), self.num_trainers):
            trainer_id = f"T{self._trainer_counter:05d}"

            trainer_data = {
                "CHOKYOSHI_CODE": trainer_id,
                "CHOKYOSHIMEI": f"調教師{i+1:03d}",
                "CHOKYOSHIMEI_RYAKUSHO": f"調{i+1:03d}",
                "SEINENGAPPI": (
                    date(1950, 1, 1) + timedelta(days=random.randint(0, 25550))
                ).strftime("%Y%m%d"),
                "SEIBETSU_CODE": "1",
                "TOZAI_SHOZOKU_CODE": random.choice(["1", "2"]),
                "INSERT_TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "UPDATE_TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            self.trainers_master.append(trainer_data)
            self._trainer_counter += 1

        logger.info(f"調教師マスター生成完了: {len(self.trainers_master):,} 人")

    def _generate_owners_master(self):
        """馬主マスターデータを生成"""
        logger.info("馬主マスター生成開始")

        for i, name in enumerate(OWNER_NAMES):
            owner_id = f"O{self._owner_counter:06d}"

            owner_data = {
                "BANUSHI_CODE": owner_id,
                "BANUSHIMEI": name,
                "HOJIN_KUBUN": random.choice(["1", "2"]),  # 1:法人, 2:個人
                "INSERT_TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "UPDATE_TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            self.owners_master.append(owner_data)
            self._owner_counter += 1

        logger.info(f"馬主マスター生成完了: {len(self.owners_master):,} 人")

    def _generate_races_and_entries(self):
        """レースデータと出走データを生成"""
        logger.info("レース・出走データ生成開始")

        current_date = self.start_date

        while current_date <= self.end_date:
            # 開催があるかチェック
            if self._should_have_racing(current_date):
                keibajo_code = self._get_keibajo_for_date(current_date)
                race_count = random.randint(*RACES_PER_DAY_RANGE)

                # その日のレースを生成
                for race_num in range(1, race_count + 1):
                    race_data = self._generate_single_race(
                        current_date, keibajo_code, race_num
                    )
                    self.races_data.append(race_data)

                    # 出走データを生成
                    entries = self._generate_race_entries(race_data)
                    self.race_entries_data.extend(entries)

            current_date += timedelta(days=1)

        logger.info(f"レース生成完了: {len(self.races_data):,} レース")
        logger.info(f"出走データ生成完了: {len(self.race_entries_data):,} 件")

    def _should_have_racing(self, target_date: date) -> bool:
        """指定日に開催があるかを判定"""
        # 土日を中心とした開催パターン
        weekday = target_date.weekday()

        # 土日は高確率で開催
        if weekday in [5, 6]:  # 土曜、日曜
            return random.random() < 0.8
        # 祝日や特別開催日をシミュレート
        if weekday in [0]:  # 月曜（祝日等）
            return random.random() < 0.3
        return False

    def _get_keibajo_for_date(self, target_date: date) -> str:
        """指定日の開催競馬場を決定"""
        month = target_date.month
        if month in KAISAI_SCHEDULE:
            keibajo_options = [keibajo[0] for keibajo in KAISAI_SCHEDULE[month]]
            return random.choice(keibajo_options)
        return random.choice(list(KEIBAJO_MASTER.keys()))

    def _generate_single_race(
        self, race_date: date, keibajo_code: str, race_num: int
    ) -> dict:
        """単一レースのデータを生成"""
        race_id = f"R{self._race_counter:010d}"

        # グレード・条件決定
        if race_num == 11:  # メインレース
            grade_code = random.choice(["1", "2", "3", "5"])
        else:
            grade_code = random.choice(["A", "B", "C", "D", "E"])

        # 距離・コース決定
        track_type = random.choice(["芝", "ダート"])
        distance = random.choice(DISTANCES[track_type])

        track_code = random.choice(list(TRACK_CODES.keys()))
        # track_condition = random.choice(list(TRACK_CONDITIONS.keys()))

        # レース名生成
        race_name = self._generate_race_name(grade_code, keibajo_code)

        race_data = {
            "RACE_CODE": race_id,
            "KAISAI_NEN": race_date.strftime("%Y"),
            "KAISAI_GAPPI": race_date.strftime("%m%d"),
            "KEIBAJO_CODE": keibajo_code,
            "RACE_BANGO": f"{race_num:02d}",
            "KYOSOMEI_HONDAI": race_name,
            "GRADE_CODE": grade_code,
            "KYORI": f"{distance:04d}",
            "TRACK_CODE": track_code,
            "HONSHOKIN1": str(self._calculate_prize_money(grade_code, 1)),
            "HONSHOKIN2": str(self._calculate_prize_money(grade_code, 2)),
            "HONSHOKIN3": str(self._calculate_prize_money(grade_code, 3)),
            "INSERT_TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "UPDATE_TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        self._race_counter += 1
        return race_data

    def _generate_race_name(self, grade_code: str, keibajo_code: str) -> str:
        """レース名を生成"""
        if grade_code in ["1", "2", "3"] and random.random() < 0.7:
            # 有名重賞名を使用
            grade_name = GRADE_CODES[grade_code]
            if grade_name in FAMOUS_RACE_NAMES:
                return random.choice(FAMOUS_RACE_NAMES[grade_name])

        # 通常のレース名生成
        keibajo_name = KEIBAJO_MASTER[keibajo_code]

        templates = [
            f"{keibajo_name}記念",
            f"{keibajo_name}ステークス",
            f"{keibajo_name}特別",
            f"{keibajo_name}杯",
            "新馬戦",
            "未勝利戦",
            "1勝クラス",
            "2勝クラス",
            "3勝クラス",
        ]

        return random.choice(templates)

    def _calculate_prize_money(self, grade_code: str, position: int) -> int:
        """着順別賞金を計算"""
        base_prizes = {
            "1": [300000000, 120000000, 75000000],  # G1
            "2": [60000000, 24000000, 15000000],  # G2
            "3": [40000000, 16000000, 10000000],  # G3
            "5": [20000000, 8000000, 5000000],  # OP
            "A": [10000000, 4000000, 2500000],  # 3勝
            "B": [7500000, 3000000, 1900000],  # 2勝
            "C": [5000000, 2000000, 1200000],  # 1勝
            "D": [5000000, 2000000, 1200000],  # 新馬
            "E": [5000000, 2000000, 1200000],  # 未勝利
        }

        if position <= 3:
            return base_prizes.get(grade_code, base_prizes["E"])[position - 1]
        return int(base_prizes.get(grade_code, base_prizes["E"])[2] * 0.3)

    def _generate_race_entries(self, race_data: dict) -> list[dict]:
        """レースの出走データを生成"""
        race_id = race_data["RACE_CODE"]
        num_horses = random.randint(*HORSES_PER_RACE_RANGE)

        entries = []
        selected_horses = random.sample(self.horses_master, num_horses)

        # 着順をランダムに決定（重複なし）
        finish_positions = list(range(1, num_horses + 1))
        random.shuffle(finish_positions)

        for i, horse in enumerate(selected_horses):
            jockey = random.choice(self.jockeys_master)
            owner = random.choice(self.owners_master)

            # タイム計算（現実的な範囲）
            distance = int(race_data["KYORI"])
            base_time = self._calculate_realistic_time(distance)
            finish_position = finish_positions[i]

            # 着順に応じたタイム調整
            time_penalty = (finish_position - 1) * random.uniform(0.1, 0.8)
            finish_time = base_time + time_penalty

            entry_data = {
                "RACE_CODE": race_id,
                "KETTO_TOROKU_BANGO": horse["KETTO_TOROKU_BANGO"],
                "KAISAI_NEN": race_data["KAISAI_NEN"],
                "KAISAI_GAPPI": race_data["KAISAI_GAPPI"],
                "KEIBAJO_CODE": race_data["KEIBAJO_CODE"],
                "RACE_BANGO": race_data["RACE_BANGO"],
                "WAKUBAN": str((i % 8) + 1),  # 1-8枠
                "UMABAN": f"{i + 1:02d}",
                "BAMEI": horse["BAMEI"],
                "SEIBETSU_CODE": horse["SEIBETSU_CODE"],
                "BAREI": str(self._calculate_age(horse["SEINENGAPPI"], race_data)),
                "CHOKYOSHI_CODE": horse["CHOKYOSHI_CODE"],
                "KISHU_CODE": jockey["KISHU_CODE"],
                "KISHUMEI_RYAKUSHO": jockey["KISHUMEI_RYAKUSHO"],
                "BANUSHI_CODE": owner["BANUSHI_CODE"],
                "FUTAN_JURYO": str(random.randint(52, 60)),  # 52-60kg
                "BATAIJU": str(random.randint(420, 520)),  # 体重
                "NYUSEN_JUNI": f"{finish_position:02d}",
                "KAKUTEI_CHAKUJUN": f"{finish_position:02d}",
                "SOHA_TIME": self._format_time(finish_time),
                "INSERT_TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "UPDATE_TIMESTAMP": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            entries.append(entry_data)

        return entries

    def _calculate_age(self, birth_date_str: str, race_data: dict) -> int:
        """馬齢を計算"""
        try:
            birth_date = datetime.strptime(birth_date_str, "%Y%m%d").date()
            race_year = int(race_data["KAISAI_NEN"])
            return race_year - birth_date.year
        except:
            return random.randint(3, 8)  # デフォルト

    def _calculate_realistic_time(self, distance: int) -> float:
        """距離に応じた現実的なタイムを計算（秒）"""
        # 距離別基準タイム（おおよそのレコードタイム）
        base_times = {
            1000: 56.0,
            1200: 68.0,
            1400: 80.0,
            1600: 92.0,
            1800: 108.0,
            2000: 120.0,
            2200: 132.0,
            2400: 144.0,
            2500: 150.0,
            3000: 186.0,
            3200: 200.0,
            3400: 214.0,
        }

        # 最も近い距離の基準タイムを取得
        closest_distance = min(base_times.keys(), key=lambda x: abs(x - distance))
        base_time = base_times[closest_distance]

        # 距離差による補正
        time_adjustment = (distance - closest_distance) * 0.06  # 100mあたり6秒
        base_time += time_adjustment

        # ランダムな変動を追加
        variation = random.uniform(-2.0, 8.0)

        return base_time + variation

    def _format_time(self, seconds: float) -> str:
        """秒をmm:ss.sフォーマットに変換"""
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes:02d}{remaining_seconds:04.1f}"

    def save_to_csv(self, output_dir: str = "data/mock_output"):
        """生成したデータをCSVファイルとして保存

        Args:
            output_dir: 出力ディレクトリ
        """
        import os

        os.makedirs(output_dir, exist_ok=True)

        dataframes = self.generate_all_data()

        for table_name, df in dataframes.items():
            file_path = f"{output_dir}/{table_name}.csv"
            df.to_csv(file_path, index=False, encoding="utf-8")
            logger.info(f"CSV出力完了: {file_path} ({len(df):,} 件)")

    def get_feature_extraction_data(self) -> dict[str, pd.DataFrame]:
        """特徴量抽出用のフォーマット済みデータを取得

        Returns:
            特徴量抽出器で使用可能な形式のデータ
        """
        logger.info("特徴量抽出用データ形式変換開始")

        raw_data = self.generate_all_data()

        # レースデータの統合と変換
        races_df = self._convert_race_data(raw_data)
        history_df = self._create_history_data(raw_data)

        return {
            "races": races_df,
            "history": history_df,
        }

    def _convert_race_data(self, raw_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """レースデータを特徴量抽出用に変換"""
        races = raw_data["races"]
        entries = raw_data["race_entries"]

        # 結合して統合データを作成
        race_data = entries.merge(
            races, on="RACE_CODE", how="left", suffixes=("_entry", "_race")
        )

        # カラム名を特徴量抽出器が期待する形式に変換
        converted = race_data.rename(
            columns={
                "RACE_CODE": "race_id",
                "KETTO_TOROKU_BANGO": "horse_id",
                "KISHU_CODE": "jockey_id",
                "CHOKYOSHI_CODE": "trainer_id",
                "KYORI": "distance",
                "KEIBAJO_CODE_entry": "venue_code",
                "GRADE_CODE": "race_class",
                "KAKUTEI_CHAKUJUN": "finish_position",
                "SOHA_TIME": "finish_time",
                "FUTAN_JURYO": "weight_carried",
            }
        ).copy()

        # データ型変換
        converted["distance"] = pd.to_numeric(converted["distance"], errors="coerce")
        converted["finish_position"] = pd.to_numeric(
            converted["finish_position"], errors="coerce"
        )
        converted["weight_carried"] = pd.to_numeric(
            converted["weight_carried"], errors="coerce"
        )

        # 日付変換 - どちらのカラムセットを使うか確認
        kaisai_nen_col = (
            "KAISAI_NEN_entry"
            if "KAISAI_NEN_entry" in race_data.columns
            else "KAISAI_NEN"
        )
        kaisai_gappi_col = (
            "KAISAI_GAPPI_entry"
            if "KAISAI_GAPPI_entry" in race_data.columns
            else "KAISAI_GAPPI"
        )

        converted["race_date"] = pd.to_datetime(
            race_data[kaisai_nen_col] + race_data[kaisai_gappi_col], format="%Y%m%d"
        )

        # 必要なカラムのみ選択
        result_columns = [
            "race_id",
            "horse_id",
            "jockey_id",
            "trainer_id",
            "distance",
            "venue_code",
            "race_class",
            "finish_position",
            "finish_time",
            "weight_carried",
            "race_date",
        ]

        result = converted[result_columns].copy()

        # venue名を追加
        venue_mapping = KEIBAJO_MASTER
        result["venue"] = result["venue_code"].map(venue_mapping)

        # track_type, track_conditionなど追加の特徴量
        result["track_type"] = "turf"  # 簡略化
        result["track_condition"] = "good"  # 簡略化
        result["post_position"] = range(1, len(result) + 1)  # 簡略化

        logger.info(f"レースデータ変換完了: {len(result):,} 件")
        return result

    def _create_history_data(self, raw_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """過去成績データを作成"""
        race_data = self._convert_race_data(raw_data)

        # 各馬の過去成績として全レコードを使用
        # （時系列順序は race_date で管理）
        history_df = race_data.copy()

        logger.info(f"過去成績データ作成完了: {len(history_df):,} 件")
        return history_df
