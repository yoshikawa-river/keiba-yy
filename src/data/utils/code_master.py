"""
JRA-VANコードマスター

JRA-VANの各種コードを意味のある値に変換するユーティリティ
"""

from typing import Optional


class CodeMaster:
    """JRA-VANコードマスター"""

    # 競馬場コード
    JYO_CODES = {
        "01": "札幌",
        "02": "函館",
        "03": "福島",
        "04": "新潟",
        "05": "東京",
        "06": "中山",
        "07": "中京",
        "08": "京都",
        "09": "阪神",
        "10": "小倉",
        # 地方競馬場
        "30": "門別",
        "35": "盛岡",
        "36": "水沢",
        "42": "浦和",
        "43": "船橋",
        "44": "大井",
        "45": "川崎",
        "46": "金沢",
        "47": "笠松",
        "48": "名古屋",
        "50": "園田",
        "51": "姫路",
        "54": "高知",
        "55": "佐賀",
        # 海外
        "A0": "香港",
        "A2": "アメリカ",
        "A4": "イギリス",
        "A6": "フランス",
        "A8": "アイルランド",
        "B0": "ニュージーランド",
        "B2": "オーストラリア",
        "B4": "シンガポール",
        "B6": "スウェーデン",
        "B8": "マカオ",
        "C0": "ドイツ",
        "C2": "カナダ",
        "C4": "イタリア",
        "C6": "UAE",
        "C8": "ブラジル",
        "D0": "ベルギー",
        "D2": "トルコ",
        "D4": "カタール",
        "D6": "韓国",
        "D8": "インド",
        "E0": "その他海外",
    }

    # 性別コード
    SEX_CODES = {"1": "牡", "2": "牝", "3": "セ"}

    # 毛色コード
    KEIRO_CODES = {
        "01": "栗毛",
        "02": "栃栗毛",
        "03": "鹿毛",
        "04": "黒鹿毛",
        "05": "青鹿毛",
        "06": "青毛",
        "07": "芦毛",
        "08": "栗粕毛",
        "09": "鹿粕毛",
        "10": "青粕毛",
        "11": "白毛",
    }

    # 馬記号コード
    UMA_KIGO_CODES = {
        "00": "(抹消)",
        "01": "(地)",
        "02": "(外)",
        "03": "(市)",
        "04": "(市)(地)",
        "05": "(市)(外)",
        "06": "父",
        "07": "市",
        "08": "新",
        "09": "父市",
        "10": "父新",
        "11": "市地",
        "12": "外地",
        "13": "父地",
        "14": "父外",
        "15": "父市地",
        "21": "(招待)",
        "26": "地",
        "27": "外",
        "31": "(持ち込み馬)",
        "40": "九州産限定",
        "41": "(市)(九州産限定)",
    }

    # トラックコード
    TRACK_CODES = {
        # 芝
        "10": "芝",
        "11": "芝・外",
        "12": "芝・内",
        "13": "芝・内2周",
        "14": "芝・外2周",
        "15": "芝・外→内",
        "16": "芝・内→外",
        "17": "芝・直線",
        "18": "芝・その他",
        "19": "芝・2歳",
        # ダート
        "20": "ダート",
        "21": "ダート・外",
        "22": "ダート・内",
        "23": "ダート・内2周",
        "24": "ダート・外2周",
        "25": "ダート・外→内",
        "26": "ダート・内→外",
        "27": "ダート・直線",
        "28": "ダート・その他",
        "29": "ダート・2歳",
        # サンド
        "30": "サンド",
        # 障害
        "51": "障害・芝",
        "52": "障害・芝ダート",
        "53": "障害・芝→ダート",
        "54": "障害・ダート→芝→ダート",
        "55": "障害・芝→ダート→芝",
        "56": "障害・芝・2周以上",
        "57": "障害・芝・その他",
        "58": "障害・ダート",
        "59": "障害・ダート・その他",
    }

    # 種別コード
    SYUBETU_CODES = {
        "00": "該当なし",
        "11": "2歳",
        "12": "3歳",
        "13": "3歳以上",
        "14": "4歳以上",
        "18": "3～4歳",
        "19": "その他平地",
        "21": "障害3歳以上",
        "22": "障害4歳以上",
        "23": "その他障害",
    }

    # グレードコード
    GRADE_CODES = {
        "A": "G1",
        "B": "G2",
        "C": "G3",
        "D": "重賞",
        "E": "特別",
        "F": "L（リステッド）",
        " ": "",  # 平場
    }

    # 重量コード
    JYURYO_CODES = {"1": "ハンデキャップ", "2": "別定", "3": "馬齢", "4": "定量"}

    # 天候コード
    TENKO_CODES = {"1": "晴", "2": "曇", "3": "雨", "4": "小雨", "5": "小雪", "6": "雪"}

    # 馬場状態コード
    BABA_CODES = {"1": "良", "2": "稍重", "3": "重", "4": "不良"}

    # 東西所属コード
    TOZAI_CODES = {"1": "美浦", "2": "栗東", "3": "地方", "4": "海外"}

    # 異常区分コード
    IJYO_CODES = {
        "0": "",  # 正常
        "1": "取消",
        "2": "競走中止",
        "3": "出走取消",
        "4": "競走除外",
        "5": "失格",
        "6": "降着",
    }

    # 曜日コード
    YOUBI_CODES = {
        "1": "月",
        "2": "火",
        "3": "水",
        "4": "木",
        "5": "金",
        "6": "土",
        "7": "日",
    }

    # 見習い区分
    MINARAI_CODES = {
        "0": "",  # 通常
        "1": "☆",  # 減量1キロ
        "2": "△",  # 減量2キロ
        "3": "▲",  # 減量3キロ
    }

    # 品種コード
    HINSYU_CODES = {
        "1": "サラブレッド",
        "2": "サラブレッド系",
        "3": "準サラブレッド",
        "4": "ライトハーフリンガー",
        "5": "アングロアラブ",
        "6": "アラブ系",
        "7": "アラブ",
        "8": "ミュール",
        "9": "クォーターホース",
    }

    @classmethod
    def get_jyo_name(cls, code: str) -> str:
        """競馬場コードから名前を取得"""
        return cls.JYO_CODES.get(code, "不明")

    @classmethod
    def get_sex_name(cls, code: str) -> str:
        """性別コードから名前を取得"""
        return cls.SEX_CODES.get(code, "不明")

    @classmethod
    def get_keiro_name(cls, code: str) -> str:
        """毛色コードから名前を取得"""
        return cls.KEIRO_CODES.get(code, "不明")

    @classmethod
    def get_uma_kigo(cls, code: str) -> str:
        """馬記号コードから記号を取得"""
        return cls.UMA_KIGO_CODES.get(code, "")

    @classmethod
    def get_track_type(cls, code: str) -> str:
        """トラックコードから種別を取得"""
        track_info = cls.TRACK_CODES.get(code, "不明")
        if "芝" in track_info and "障害" not in track_info:
            return "芝"
        if "ダート" in track_info and "障害" not in track_info:
            return "ダート"
        if "サンド" in track_info:
            return "サンド"
        if "障害" in track_info:
            return "障害"
        return "不明"

    @classmethod
    def get_track_detail(cls, code: str) -> str:
        """トラックコードから詳細を取得"""
        return cls.TRACK_CODES.get(code, "不明")

    @classmethod
    def get_syubetu(cls, code: str) -> str:
        """種別コードから名前を取得"""
        return cls.SYUBETU_CODES.get(code, "不明")

    @classmethod
    def get_grade(cls, code: str) -> str:
        """グレードコードから名前を取得"""
        return cls.GRADE_CODES.get(code, "")

    @classmethod
    def get_jyuryo(cls, code: str) -> str:
        """重量コードから名前を取得"""
        return cls.JYURYO_CODES.get(code, "不明")

    @classmethod
    def get_tenko(cls, code: str) -> str:
        """天候コードから名前を取得"""
        return cls.TENKO_CODES.get(code, "不明")

    @classmethod
    def get_baba(cls, code: str) -> str:
        """馬場状態コードから名前を取得"""
        return cls.BABA_CODES.get(code, "不明")

    @classmethod
    def get_tozai(cls, code: str) -> str:
        """東西所属コードから名前を取得"""
        return cls.TOZAI_CODES.get(code, "不明")

    @classmethod
    def get_ijyo(cls, code: str) -> str:
        """異常区分コードから名前を取得"""
        return cls.IJYO_CODES.get(code, "")

    @classmethod
    def get_youbi(cls, code: str) -> str:
        """曜日コードから名前を取得"""
        return cls.YOUBI_CODES.get(code, "不明")

    @classmethod
    def get_minarai(cls, code: str) -> str:
        """見習い区分から記号を取得"""
        return cls.MINARAI_CODES.get(code, "")

    @classmethod
    def get_hinsyu(cls, code: str) -> str:
        """品種コードから名前を取得"""
        return cls.HINSYU_CODES.get(code, "サラブレッド")

    @classmethod
    def convert_time(cls, time_str: str) -> Optional[float]:
        """
        タイム文字列を秒数に変換
        "0593" -> 59.3秒
        "1234" -> 123.4秒 (2分3秒4)
        """
        if not time_str or len(time_str) != 4:
            return None

        try:
            # 最初の3桁が秒数、最後の1桁が小数点以下
            seconds = int(time_str[0:3])
            decimal = int(time_str[3])
            return seconds + decimal / 10
        except (ValueError, TypeError):
            return None

    @classmethod
    def convert_odds(cls, odds_str: str) -> Optional[float]:
        """
        オッズ文字列を数値に変換
        "0123" -> 12.3
        "9999" -> 999.9
        """
        if not odds_str:
            return None

        try:
            return float(odds_str) / 10
        except (ValueError, TypeError):
            return None

    @classmethod
    def convert_weight(cls, weight_str: str) -> Optional[float]:
        """
        斤量文字列を数値に変換
        "560" -> 56.0
        "55" -> 55.0
        """
        if not weight_str:
            return None

        try:
            weight = float(weight_str)
            # 3桁の場合は10で割る
            if weight >= 100:
                return weight / 10
            return weight
        except (ValueError, TypeError):
            return None

    @classmethod
    def convert_distance(cls, distance_str: str) -> Optional[int]:
        """
        距離文字列を数値に変換
        "1200" -> 1200
        """
        if not distance_str:
            return None

        try:
            return int(distance_str)
        except (ValueError, TypeError):
            return None

    @classmethod
    def convert_money(cls, money_str: str) -> Optional[int]:
        """
        賞金文字列を数値に変換（万円単位）
        "12345678" -> 12345678万円
        """
        if not money_str:
            return 0

        try:
            return int(money_str)
        except (ValueError, TypeError):
            return 0

    @classmethod
    def format_race_key(
        cls, year: str, jyo_cd: str, kaiji: str, nichiji: str, race_num: str
    ) -> str:
        """
        レースキーをフォーマット
        "2024", "05", "01", "01", "01" -> "2024050101"
        """
        return f"{year}{jyo_cd}{kaiji}{nichiji}{race_num}"

    @classmethod
    def parse_race_key(cls, race_key: str) -> dict[str, str]:
        """
        レースキーをパース
        "2024050101" -> {"year": "2024", "jyo_cd": "05", ...}
        """
        if len(race_key) < 10:
            raise ValueError(f"Invalid race key format: {race_key}")

        return {
            "year": race_key[0:4],
            "jyo_cd": race_key[4:6],
            "kaiji": race_key[6:8],
            "nichiji": race_key[8:10],
            "race_num": race_key[10:12] if len(race_key) >= 12 else "01",
        }

    @classmethod
    def get_chakusa_text(cls, chakusa_cd: str) -> str:
        """
        着差コードからテキストを取得
        """
        chakusa_map = {
            "000": "",  # 同着
            "001": "アタマ",
            "002": "クビ",
            "003": "ハナ",
            "004": "1/2",
            "005": "3/4",
            "006": "1",
            "007": "1 1/4",
            "008": "1 1/2",
            "009": "1 3/4",
            "010": "2",
            "011": "2 1/2",
            "012": "3",
            "013": "3 1/2",
            "014": "4",
            "015": "5",
            "016": "6",
            "017": "7",
            "018": "8",
            "019": "9",
            "020": "10",
            "999": "大差",
        }

        if not chakusa_cd:
            return ""

        # 数値の場合はそのまま使用
        try:
            code = int(chakusa_cd)
            if code <= 20:
                return chakusa_map.get(f"{code:03d}", f"{code}")
            if code >= 999:
                return "大差"
            # 21以上は馬身数をそのまま返す
            return str(code)
        except:
            return ""
