import builtins
import contextlib
from datetime import date, datetime, time
from typing import Any, Optional

from src.data.utils.code_master import CodeMaster

"""
データコンバーター

mykeibaDBデータ形式と内部形式の変換
"""


class RaceKey:
    """レースを特定する複合キー"""

    def __init__(self, year: str, jyo_cd: str, kaiji: str, nichiji: str, race_num: str):
        self.year = year
        self.jyo_cd = jyo_cd
        self.kaiji = kaiji
        self.nichiji = nichiji
        self.race_num = race_num

    @classmethod
    def from_race_id(cls, race_id: str):
        """
        レースIDから複合キーを生成
        race_id: "2024010105010101" 形式
        """
        if len(race_id) < 14:
            raise ValueError(f"Invalid race_id format: {race_id}")

        year = race_id[0:4]
        race_id[4:8]  # これは使わない（MonthDayは別途格納）
        jyo_cd = race_id[8:10]
        kaiji = race_id[10:12]
        nichiji = race_id[12:14]
        race_num = race_id[14:16] if len(race_id) >= 16 else "01"

        return cls(year, jyo_cd, kaiji, nichiji, race_num)

    @classmethod
    def from_dict(cls, data: dict[str, str]):
        """辞書から複合キーを生成"""
        return cls(
            year=data.get("Year", ""),
            jyo_cd=data.get("JyoCD", ""),
            kaiji=data.get("Kaiji", ""),
            nichiji=data.get("Nichiji", ""),
            race_num=data.get("RaceNum", ""),
        )

    def to_dict(self):
        """辞書形式で返す（クエリ用）"""
        return {
            "Year": self.year,
            "JyoCD": self.jyo_cd,
            "Kaiji": self.kaiji,
            "Nichiji": self.nichiji,
            "RaceNum": self.race_num,
        }

    def to_race_id(self, month_day: str = ""):
        """レースID形式で返す"""
        # MonthDayが提供されていない場合は空文字
        return f"{self.year}{month_day}{self.jyo_cd}{self.kaiji}{self.nichiji}{self.race_num}"


class DataConverter:
    """JRA-VANデータ形式と内部形式の変換"""

    @staticmethod
    def parse_date(date_str: str) -> Optional[date]:
        """
        日付文字列をdateオブジェクトに変換
        "20240101" -> date(2024, 1, 1)
        """
        if not date_str or len(date_str) != 8:
            return None

        try:
            return datetime.strptime(date_str, "%Y%m%d").date()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def parse_time(time_str: str) -> Optional[time]:
        """
        時刻文字列をtimeオブジェクトに変換
        "1530" -> time(15, 30)
        """
        if not time_str or len(time_str) != 4:
            return None

        try:
            return datetime.strptime(time_str, "%H%M").time()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def nrace_to_dict(nrace) -> dict[str, Any]:  # type: ignore
        """N_RACEをビジネスロジック用の辞書に変換"""
        # レース日付の構築
        race_date = None
        if nrace.Year and nrace.MonthDay:
            race_date = DataConverter.parse_date(f"{nrace.Year}{nrace.MonthDay}")

        # 賞金情報の構築
        prize_money = {
            "1st": CodeMaster.convert_money(nrace.Honsyokin1),
            "2nd": CodeMaster.convert_money(nrace.Honsyokin2),
            "3rd": CodeMaster.convert_money(nrace.Honsyokin3),
            "4th": CodeMaster.convert_money(nrace.Honsyokin4),
            "5th": CodeMaster.convert_money(nrace.Honsyokin5),
        }

        # ラップタイムの収集
        lap_times = []
        for i in range(1, 26):  # LapTime1からLapTime25まで
            lap_attr = f"LapTime{i}"
            if hasattr(nrace, lap_attr):
                lap_time = getattr(nrace, lap_attr)
                if lap_time:
                    lap_times.append(CodeMaster.convert_time(lap_time))

        # 馬場状態の判定（芝/ダート別）
        track_type = CodeMaster.get_track_type(nrace.TrackCD)
        if track_type == "芝":
            track_condition = CodeMaster.get_baba(nrace.SibaBabaCD)
        else:
            track_condition = CodeMaster.get_baba(nrace.DirtBabaCD)

        return {
            # 識別情報
            "race_id": f"{nrace.Year}{nrace.MonthDay}{nrace.JyoCD}{nrace.Kaiji}{nrace.Nichiji}{nrace.RaceNum}",
            "race_key": RaceKey(
                nrace.Year, nrace.JyoCD, nrace.Kaiji, nrace.Nichiji, nrace.RaceNum
            ),
            # 基本情報
            "race_date": race_date,
            "year": int(nrace.Year) if nrace.Year else None,
            "month_day": nrace.MonthDay,
            "racecourse": CodeMaster.get_jyo_name(nrace.JyoCD),
            "racecourse_code": nrace.JyoCD,
            "kaiji": int(nrace.Kaiji) if nrace.Kaiji else None,
            "nichiji": int(nrace.Nichiji) if nrace.Nichiji else None,
            "race_number": int(nrace.RaceNum) if nrace.RaceNum else None,
            "youbi": CodeMaster.get_youbi(nrace.YoubiCD),
            # レース名
            "race_name": nrace.Hondai,
            "race_name_sub": nrace.Fukudai,
            "race_name_kakko": nrace.Kakko,
            "race_name_short": nrace.Ryakusyo10,
            # グレード・条件
            "grade": CodeMaster.get_grade(nrace.GradeCD),
            "grade_code": nrace.GradeCD,
            "syubetu": CodeMaster.get_syubetu(nrace.SyubetuCD),
            "jyuryo": CodeMaster.get_jyuryo(nrace.JyuryoCD),
            # コース情報
            "track_type": track_type,
            "track_detail": CodeMaster.get_track_detail(nrace.TrackCD),
            "track_code": nrace.TrackCD,
            "distance": CodeMaster.convert_distance(nrace.Kyori),
            "course_kubun": nrace.CourseKubunCD,
            # 天候・馬場
            "weather": CodeMaster.get_tenko(nrace.TenkoCD),
            "weather_code": nrace.TenkoCD,
            "track_condition": track_condition,
            "track_condition_code": nrace.SibaBabaCD or nrace.DirtBabaCD,
            # 頭数
            "entry_count": int(nrace.SyussoTosu) if nrace.SyussoTosu else 0,
            "toroku_count": int(nrace.TorokuTosu) if nrace.TorokuTosu else 0,
            # 時刻
            "start_time": DataConverter.parse_time(nrace.HassoTime),
            # 賞金
            "prize_money": prize_money,
            # ラップタイム
            "lap_times": lap_times,
            "pace_s3": CodeMaster.convert_time(nrace.HaronTimeS3),
            "pace_l3": CodeMaster.convert_time(nrace.HaronTimeL3),
            # メタ情報
            "data_kubun": nrace.DataKubun,
            "make_date": nrace.MakeDate,
        }

    @staticmethod
    def numa_to_dict(numa) -> dict[str, Any]:  # type: ignore
        """N_UMAをビジネスロジック用の辞書に変換"""
        # 生年月日の変換
        birth_date = DataConverter.parse_date(numa.BirthDate)

        # 血統情報の構築
        pedigree = {
            "father": {
                "id": numa.Ketto3InfoHansyokuNum1,
                "name": numa.Ketto3InfoBamei1,
            },
            "mother": {
                "id": numa.Ketto3InfoHansyokuNum2,
                "name": numa.Ketto3InfoBamei2,
            },
            "father_father": {
                "id": numa.Ketto3InfoHansyokuNum3,
                "name": numa.Ketto3InfoBamei3,
            },
            "father_mother": {
                "id": numa.Ketto3InfoHansyokuNum4,
                "name": numa.Ketto3InfoBamei4,
            },
            "mother_father": {
                "id": numa.Ketto3InfoHansyokuNum5,
                "name": numa.Ketto3InfoBamei5,
            },
            "mother_mother": {
                "id": numa.Ketto3InfoHansyokuNum6,
                "name": numa.Ketto3InfoBamei6,
            },
        }

        # 成績統計
        performance = {
            "total_races": int(numa.ChakuSogo6) if numa.ChakuSogo6 else 0,
            "wins": int(numa.ChakuSogo1) if numa.ChakuSogo1 else 0,
            "seconds": int(numa.ChakuSogo2) if numa.ChakuSogo2 else 0,
            "thirds": int(numa.ChakuSogo3) if numa.ChakuSogo3 else 0,
            "total_prize_money": CodeMaster.convert_money(numa.RuikeiHonsyoHeiti),
        }

        return {
            # 識別情報
            "horse_id": numa.KettoNum,
            # 基本情報
            "name": numa.Bamei,
            "name_kana": numa.BameiKana,
            "name_eng": numa.BameiEng,
            # 属性
            "birth_date": birth_date,
            "sex": CodeMaster.get_sex_name(numa.SexCD),
            "sex_code": numa.SexCD,
            "keiro": CodeMaster.get_keiro_name(numa.KeiroCD),
            "keiro_code": numa.KeiroCD,
            "hinsyu": CodeMaster.get_hinsyu(numa.HinsyuCD),
            "uma_kigo": CodeMaster.get_uma_kigo(numa.UmaKigoCD),
            # 血統
            "pedigree": pedigree,
            # 所属
            "tozai": CodeMaster.get_tozai(numa.TozaiCD),
            "trainer_code": numa.ChokyosiCode,
            "trainer_name": numa.ChokyosiRyakusyo,
            # 生産・馬主
            "breeder_code": numa.BreederCode,
            "breeder_name": numa.BreederName,
            "sanchi": numa.SanchiName,
            "owner_code": numa.BanusiCode,
            "owner_name": numa.BanusiName,
            # 成績
            "performance": performance,
            # ステータス
            "del_kubun": numa.DelKubun,
            "del_date": DataConverter.parse_date(numa.DelDate),
            "reg_date": DataConverter.parse_date(numa.RegDate),
            # メタ情報
            "data_kubun": numa.DataKubun,
            "make_date": numa.MakeDate,
        }

    @staticmethod
    def numarace_to_dict(numarace) -> dict[str, Any]:  # type: ignore
        """N_UMA_RACEをビジネスロジック用の辞書に変換"""
        # レース日付の構築
        race_date = None
        if numarace.Year and numarace.MonthDay:
            race_date = DataConverter.parse_date(f"{numarace.Year}{numarace.MonthDay}")

        # 馬体重の変換
        horse_weight = int(numarace.BaTaijyu) if numarace.BaTaijyu else None
        weight_diff = None
        if numarace.ZogenSa:
            weight_diff = int(numarace.ZogenSa)
            if numarace.ZogenFugo == "-":
                weight_diff = -weight_diff

        # 通過順位の収集
        corner_positions = []
        for pos in [
            numarace.Jyuni1c,
            numarace.Jyuni2c,
            numarace.Jyuni3c,
            numarace.Jyuni4c,
        ]:
            if pos:
                try:
                    corner_positions.append(int(pos))
                except:
                    corner_positions.append(0)

        # 異常区分の判定
        is_normal = numarace.IJyoCD == "0" or not numarace.IJyoCD
        finish_position = None
        if is_normal and numarace.KakuteiJyuni:
            with contextlib.suppress(builtins.BaseException):
                finish_position = int(numarace.KakuteiJyuni)

        return {
            # 識別情報
            "race_id": f"{numarace.Year}{numarace.MonthDay}{numarace.JyoCD}{numarace.Kaiji}{numarace.Nichiji}{numarace.RaceNum}",
            "race_key": RaceKey(
                numarace.Year,
                numarace.JyoCD,
                numarace.Kaiji,
                numarace.Nichiji,
                numarace.RaceNum,
            ),
            "horse_id": numarace.KettoNum,
            # レース情報
            "race_date": race_date,
            "racecourse": CodeMaster.get_jyo_name(numarace.JyoCD),
            # 馬情報
            "horse_name": numarace.Bamei,
            "horse_number": int(numarace.Umaban) if numarace.Umaban else None,
            "post_position": int(numarace.Wakuban) if numarace.Wakuban else None,
            "sex": CodeMaster.get_sex_name(numarace.SexCD),
            "age": int(numarace.Barei) if numarace.Barei else None,
            "keiro": CodeMaster.get_keiro_name(numarace.KeiroCD),
            "uma_kigo": CodeMaster.get_uma_kigo(numarace.UmaKigoCD),
            # 騎手・調教師
            "jockey_code": numarace.KisyuCode,
            "jockey_name": numarace.KisyuRyakusyo,
            "jockey_minarai": CodeMaster.get_minarai(numarace.MinaraiCD),
            "trainer_code": numarace.ChokyosiCode,
            "trainer_name": numarace.ChokyosiRyakusyo,
            # 馬主
            "owner_code": numarace.BanusiCode,
            "owner_name": numarace.BanusiName,
            # 重量
            "weight_carried": CodeMaster.convert_weight(numarace.Futan),
            "horse_weight": horse_weight,
            "weight_diff": weight_diff,
            "blinker": numarace.Blinker == "1",
            # レース結果
            "finish_position": finish_position,
            "finish_time": CodeMaster.convert_time(numarace.Time),
            "odds_win": CodeMaster.convert_odds(numarace.Odds),
            "popularity": int(numarace.Ninki) if numarace.Ninki else None,
            "prize_money": CodeMaster.convert_money(numarace.Honsyokin),
            # 詳細結果
            "corner_positions": corner_positions,
            "last_3f": CodeMaster.convert_time(numarace.HaronTimeL3),
            "last_4f": CodeMaster.convert_time(numarace.HaronTimeL4),
            "time_diff": CodeMaster.convert_time(numarace.TimeDiff),
            # 着差
            "chakusa": CodeMaster.get_chakusa_text(numarace.ChakusaCD),
            "chakusa_code": numarace.ChakusaCD,
            # 異常
            "ijyo": CodeMaster.get_ijyo(numarace.IJyoCD),
            "ijyo_code": numarace.IJyoCD,
            "is_normal": is_normal,
            # その他
            "tozai": CodeMaster.get_tozai(numarace.TozaiCD),
            "kyakusitu": numarace.KyakusituKubun,
            # メタ情報
            "data_kubun": numarace.DataKubun,
            "make_date": numarace.MakeDate,
        }

    @staticmethod
    def nkisyu_to_dict(nkisyu) -> dict[str, Any]:  # type: ignore
        """N_KISYUをビジネスロジック用の辞書に変換"""
        return {
            # 識別情報
            "jockey_id": nkisyu.KisyuCode,
            # 基本情報
            "name": nkisyu.KisyuName,
            "name_kana": nkisyu.KisyuNameKana,
            "name_eng": nkisyu.KisyuNameEng,
            "ryakusyo": nkisyu.KisyuRyakusyo,
            # 属性
            "birth_date": DataConverter.parse_date(nkisyu.BirthDate),
            "sex": CodeMaster.get_sex_name(nkisyu.SexCD),
            # 資格・所属
            "sikaku": nkisyu.SikakuCD,
            "minarai": CodeMaster.get_minarai(nkisyu.MinaraiCD),
            "tozai": CodeMaster.get_tozai(nkisyu.TozaiCD),
            "syotai": nkisyu.Syotai,
            # 調教師
            "trainer_code": nkisyu.ChokyosiCode,
            "trainer_name": nkisyu.ChokyosiRyakusyo,
            # ステータス
            "del_kubun": nkisyu.DelKubun,
            "issue_date": DataConverter.parse_date(nkisyu.IssueDate),
            "del_date": DataConverter.parse_date(nkisyu.DelDate),
            # メタ情報
            "data_kubun": nkisyu.DataKubun,
            "make_date": nkisyu.MakeDate,
        }

    @staticmethod
    def nchokyo_to_dict(nchokyo) -> dict[str, Any]:  # type: ignore
        """N_CHOKYOをビジネスロジック用の辞書に変換"""
        return {
            # 識別情報
            "trainer_id": nchokyo.ChokyosiCode,
            # 基本情報
            "name": nchokyo.ChokyosiName,
            "name_kana": nchokyo.ChokyosiNameKana,
            "name_eng": nchokyo.ChokyosiNameEng,
            "ryakusyo": nchokyo.ChokyosiRyakusyo,
            # 属性
            "birth_date": DataConverter.parse_date(nchokyo.BirthDate),
            "sex": CodeMaster.get_sex_name(nchokyo.SexCD),
            # 所属
            "tozai": CodeMaster.get_tozai(nchokyo.TozaiCD),
            "syotai": nchokyo.Syotai,
            # ステータス
            "del_kubun": nchokyo.DelKubun,
            "issue_date": DataConverter.parse_date(nchokyo.IssueDate),
            "del_date": DataConverter.parse_date(nchokyo.DelDate),
            # メタ情報
            "data_kubun": nchokyo.DataKubun,
            "make_date": nchokyo.MakeDate,
        }
