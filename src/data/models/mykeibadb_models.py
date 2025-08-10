"""
mykeibaDBテーブルモデル定義

実際のMySQLスキーマに対応したSQLAlchemyモデル
"""

from datetime import datetime

from sqlalchemy import Column, Index, PrimaryKeyConstraint, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class RaceShosai(Base):
    """RACE_SHOSAI - レース詳細情報"""

    __tablename__ = "RACE_SHOSAI"

    # メタ情報
    INSERT_TIMESTAMP = Column(String(19))
    UPDATE_TIMESTAMP = Column(String(19))
    RECORD_SHUBETSU_ID = Column(String(2))
    DATA_KUBUN = Column(String(1))
    DATA_SAKUSEI_NENGAPPI = Column(String(8))

    # プライマリキー
    RACE_CODE = Column(String(16), primary_key=True, nullable=False)

    # レース基本情報
    KAISAI_NEN = Column(String(4))  # 開催年
    KAISAI_GAPPI = Column(String(4))  # 開催月日
    KEIBAJO_CODE = Column(String(2))  # 競馬場コード
    KAISAI_KAI = Column(String(2))  # 開催回
    KAISAI_NICHIME = Column(String(2))  # 開催日目
    RACE_BANGO = Column(String(2))  # レース番号

    # レース詳細
    YOBI_CODE = Column(String(1))  # 曜日コード
    TOKUBETSU_KYOSO_BANGO = Column(String(4))  # 特別競走番号
    KYOSOMEI_HONDAI = Column(String(60))  # 競走名本題
    KYOSOMEI_FUKUDAI = Column(String(60))  # 競走名副題
    KYOSOMEI_KAKKONAI = Column(String(60))  # 競走名括弧内
    KYOSOMEI_HONDAI_ENG = Column(String(120))  # 競走名本題（英語）
    KYOSOMEI_FUKUDAI_ENG = Column(String(120))  # 競走名副題（英語）
    KYOSOMEI_KAKKONAI_ENG = Column(String(120))  # 競走名括弧内（英語）
    KYOSOMEI_RYAKUSHO_10 = Column(String(20))  # 競走名略称10文字
    KYOSOMEI_RYAKUSHO_6 = Column(String(12))  # 競走名略称6文字
    KYOSOMEI_RYAKUSHO_3 = Column(String(6))  # 競走名略称3文字
    KYOSOMEI_KUBUN = Column(String(1))  # 競走名区分
    JUSHO_KAIJI = Column(String(3))  # 重賞回次

    # グレード・条件
    GRADE_CODE = Column(String(1))  # グレードコード
    HENKOMAE_GRADE_CODE = Column(String(1))  # 変更前グレードコード
    KYOSO_SHUBETSU_CODE = Column(String(2))  # 競走種別コード
    KYOSO_KIGO_CODE = Column(String(3))  # 競走記号コード
    JURYO_SHUBETSU_CODE = Column(String(1))  # 重量種別コード

    # 競走条件
    KYOSO_JOKEN_CODE_2SAI = Column(String(3))  # 2歳条件
    KYOSO_JOKEN_CODE_3SAI = Column(String(3))  # 3歳条件
    KYOSO_JOKEN_CODE_4SAI = Column(String(3))  # 4歳条件
    KYOSO_JOKEN_CODE_5SAI_IJO = Column(String(3))  # 5歳以上条件
    KYOSO_JOKEN_CODE_SAIJAKUNEN = Column(String(3))  # 最若年条件
    KYOSO_JOKEN_MEISHO = Column(String(60))  # 競走条件名称

    # コース情報
    KYORI = Column(String(4))  # 距離
    HENKOMAE_KYORI = Column(String(4))  # 変更前距離
    TRACK_CODE = Column(String(2))  # トラックコード
    HENKOMAE_TRACK_CODE = Column(String(2))  # 変更前トラックコード
    COURSE_KUBUN = Column(String(2))  # コース区分
    HENKOMAE_COURSE_KUBUN = Column(String(2))  # 変更前コース区分

    # 賞金
    HONSHOKIN1 = Column(String(8))  # 本賞金1着
    HONSHOKIN2 = Column(String(8))  # 本賞金2着
    HONSHOKIN3 = Column(String(8))  # 本賞金3着
    HONSHOKIN4 = Column(String(8))  # 本賞金4着
    HONSHOKIN5 = Column(String(8))  # 本賞金5着
    HONSHOKIN6 = Column(String(8))  # 本賞金6着
    HONSHOKIN7 = Column(String(8))  # 本賞金7着

    # テーブル設定
    __table_args__ = (
        Index('idx_race_shosai_date', 'KAISAI_NEN', 'KAISAI_GAPPI'),
        Index('idx_race_shosai_keibajo', 'KEIBAJO_CODE'),
        Index('idx_race_shosai_grade', 'GRADE_CODE'),
    )

    @property
    def race_id(self):
        """レースIDを生成（互換性のため）"""
        return self.RACE_CODE

    @property
    def race_date(self):
        """日付オブジェクトを返す"""
        if self.KAISAI_NEN and self.KAISAI_GAPPI:
            try:
                return datetime.strptime(f"{self.KAISAI_NEN}{self.KAISAI_GAPPI}", "%Y%m%d").date()
            except:
                return None
        return None


class KyosobaMaster2(Base):
    """KYOSOBA_MASTER2 - 競走馬マスター"""

    __tablename__ = "KYOSOBA_MASTER2"

    # メタ情報
    INSERT_TIMESTAMP = Column(String(19))
    UPDATE_TIMESTAMP = Column(String(19))
    RECORD_SHUBETSU_ID = Column(String(2))
    DATA_KUBUN = Column(String(1))
    DATA_SAKUSEI_NENGAPPI = Column(String(8))

    # プライマリキー
    KETTO_TOROKU_BANGO = Column(String(10), primary_key=True, nullable=False)

    # 削除・登録情報
    MASSHO_KUBUN = Column(String(1))  # 抹消区分
    TOROKU_NENGAPPI = Column(String(8))  # 登録年月日
    MASSHO_NENGAPPI = Column(String(8))  # 抹消年月日

    # 馬基本情報
    SEINENGAPPI = Column(String(8))  # 生年月日
    BAMEI = Column(String(36))  # 馬名
    BAMEI_HANKAKU_KANA = Column(String(36))  # 馬名半角カナ
    BAMEI_ENG = Column(String(60))  # 馬名英語
    JRA_SHISETSU_ZAIKYU_FLAG = Column(String(1))  # JRA施設在厩フラグ

    # 馬属性
    UMAKIGO_CODE = Column(String(2))  # 馬記号コード
    SEIBETSU_CODE = Column(String(1))  # 性別コード
    HINSHU_CODE = Column(String(1))  # 品種コード
    MOSHOKU_CODE = Column(String(2))  # 毛色コード

    # 3代血統（父系）
    KETTO1_HANSHOKU_TOROKU_BANGO = Column(String(10))  # 父
    KETTO1_BAMEI = Column(String(36))
    # 母系
    KETTO2_HANSHOKU_TOROKU_BANGO = Column(String(10))  # 母
    KETTO2_BAMEI = Column(String(36))
    # 父父
    KETTO3_HANSHOKU_TOROKU_BANGO = Column(String(10))
    KETTO3_BAMEI = Column(String(36))
    # 父母
    KETTO4_HANSHOKU_TOROKU_BANGO = Column(String(10))
    KETTO4_BAMEI = Column(String(36))
    # 母父
    KETTO5_HANSHOKU_TOROKU_BANGO = Column(String(10))
    KETTO5_BAMEI = Column(String(36))
    # 母母
    KETTO6_HANSHOKU_TOROKU_BANGO = Column(String(10))
    KETTO6_BAMEI = Column(String(36))
    # 父父父
    KETTO7_HANSHOKU_TOROKU_BANGO = Column(String(10))
    KETTO7_BAMEI = Column(String(36))
    # 父父母
    KETTO8_HANSHOKU_TOROKU_BANGO = Column(String(10))
    KETTO8_BAMEI = Column(String(36))
    # 父母父
    KETTO9_HANSHOKU_TOROKU_BANGO = Column(String(10))
    KETTO9_BAMEI = Column(String(36))
    # 父母母
    KETTO10_HANSHOKU_TOROKU_BANGO = Column(String(10))
    KETTO10_BAMEI = Column(String(36))
    # 母父父
    KETTO11_HANSHOKU_TOROKU_BANGO = Column(String(10))
    KETTO11_BAMEI = Column(String(36))
    # 母父母
    KETTO12_HANSHOKU_TOROKU_BANGO = Column(String(10))
    KETTO12_BAMEI = Column(String(36))
    # 母母父
    KETTO13_HANSHOKU_TOROKU_BANGO = Column(String(10))
    KETTO13_BAMEI = Column(String(36))
    # 母母母
    KETTO14_HANSHOKU_TOROKU_BANGO = Column(String(10))
    KETTO14_BAMEI = Column(String(36))

    # 所有者情報
    TOZAI_SHOZOKU_CODE = Column(String(1))  # 東西所属コード
    CHOKYOSHI_CODE = Column(String(5))  # 調教師コード
    CHOKYOSHIMEI_RYAKUSHO = Column(String(8))  # 調教師名略称

    # テーブル設定
    __table_args__ = (
        Index('idx_kyosoba_bamei', 'BAMEI'),
        Index('idx_kyosoba_birth', 'SEINENGAPPI'),
    )


class UmagotoRaceJoho(Base):
    """UMAGOTO_RACE_JOHO - 馬ごとレース情報"""

    __tablename__ = "UMAGOTO_RACE_JOHO"

    # メタ情報
    INSERT_TIMESTAMP = Column(String(19))
    UPDATE_TIMESTAMP = Column(String(19))
    RECORD_SHUBETSU_ID = Column(String(2))
    DATA_KUBUN = Column(String(1))
    DATA_SAKUSEI_NENGAPPI = Column(String(8))

    # 複合プライマリキー（レース + 馬）
    RACE_CODE = Column(String(16), nullable=False)
    KETTO_TOROKU_BANGO = Column(String(10), nullable=False)

    # レース情報
    KAISAI_NEN = Column(String(4))
    KAISAI_GAPPI = Column(String(4))
    KEIBAJO_CODE = Column(String(2))
    KAISAI_KAIJI = Column(String(2))
    KAISAI_NICHIJI = Column(String(2))
    RACE_BANGO = Column(String(2))

    # 出走情報
    WAKUBAN = Column(String(1))  # 枠番
    UMABAN = Column(String(2))  # 馬番

    # 馬情報（デノーマライズ）
    BAMEI = Column(String(36))  # 馬名
    UMAKIGO_CODE = Column(String(2))  # 馬記号コード
    SEIBETSU_CODE = Column(String(1))  # 性別コード
    HINSHU_CODE = Column(String(1))  # 品種コード
    MOSHOKU_CODE = Column(String(2))  # 毛色コード
    BAREI = Column(String(2))  # 馬齢
    TOZAI_SHOZOKU_CODE = Column(String(1))  # 東西所属コード

    # 調教師情報
    CHOKYOSHI_CODE = Column(String(5))  # 調教師コード
    CHOKYOSHIMEI_RYAKUSHO = Column(String(8))  # 調教師名略称

    # 馬主情報
    BANUSHI_CODE = Column(String(6))  # 馬主コード
    BANUSHIMEI_HOJINKAKU_NASHI = Column(String(64))  # 馬主名（法人格なし）

    # 服色
    FUKUSHOKU_HYOJI = Column(String(60))  # 服色標示

    # 斤量
    FUTAN_JURYO = Column(String(3))  # 負担重量
    HENKOMAE_FUTAN_JURYO = Column(String(3))  # 変更前負担重量
    BLINKER_SHIYO_KUBUN = Column(String(1))  # ブリンカー使用区分

    # 騎手情報
    KISHU_CODE = Column(String(5))  # 騎手コード
    HENKOMAE_KISHU_CODE = Column(String(5))  # 変更前騎手コード
    KISHUMEI_RYAKUSHO = Column(String(8))  # 騎手名略称
    HENKOMAE_KISHUMEI_RYAKUSHO = Column(String(8))  # 変更前騎手名略称
    KISHU_MINARAI_CODE = Column(String(1))  # 騎手見習いコード
    HENKOMAE_KISHU_MINARAI_CODE = Column(String(1))  # 変更前騎手見習いコード

    # 馬体重
    BATAIJU = Column(String(3))  # 馬体重
    ZOGEN_FUGO = Column(String(1))  # 増減符号
    ZOGEN_SA = Column(String(3))  # 増減差

    # レース結果
    IJO_KUBUN_CODE = Column(String(1))  # 異常区分コード
    NYUSEN_JUNI = Column(String(2))  # 入線順位
    KAKUTEI_CHAKUJUN = Column(String(2))  # 確定着順
    DOCHAKU_KUBUN = Column(String(1))  # 同着区分
    DOCHAKU_TOSU = Column(String(1))  # 同着頭数

    # タイム
    SOHA_TIME = Column(String(4))  # 走破タイム

    # 着差
    CHAKUSA_CODE1 = Column(String(3))  # 着差コード1
    CHAKUSA_CODE2 = Column(String(3))  # 着差コード2
    CHAKUSA_CODE3 = Column(String(3))  # 着差コード3

    # 通過順位
    CORNER1_JUNI = Column(String(2))  # 1コーナー順位
    CORNER2_JUNI = Column(String(2))  # 2コーナー順位
    CORNER3_JUNI = Column(String(2))  # 3コーナー順位
    CORNER4_JUNI = Column(String(2))  # 4コーナー順位

    # テーブル設定
    __table_args__ = (
        PrimaryKeyConstraint('RACE_CODE', 'KETTO_TOROKU_BANGO'),
        Index('idx_umagoto_ketto', 'KETTO_TOROKU_BANGO'),
        Index('idx_umagoto_kishu', 'KISHU_CODE'),
        Index('idx_umagoto_chokyo', 'CHOKYOSHI_CODE'),
    )

    @property
    def race_id(self):
        """レースIDを生成（互換性のため）"""
        return self.RACE_CODE

    @property
    def race_date(self):
        """日付オブジェクトを返す"""
        if self.KAISAI_NEN and self.KAISAI_GAPPI:
            try:
                return datetime.strptime(f"{self.KAISAI_NEN}{self.KAISAI_GAPPI}", "%Y%m%d").date()
            except:
                return None
        return None


class KishuMaster(Base):
    """KISHU_MASTER - 騎手マスター"""

    __tablename__ = "KISHU_MASTER"

    # メタ情報
    INSERT_TIMESTAMP = Column(String(19))
    UPDATE_TIMESTAMP = Column(String(19))
    RECORD_SHUBETSU_ID = Column(String(2))
    DATA_KUBUN = Column(String(1))
    DATA_SAKUSEI_NENGAPPI = Column(String(8))

    # プライマリキー
    KISHU_CODE = Column(String(5), primary_key=True, nullable=False)

    # 削除・登録情報
    MASSHO_KUBUN = Column(String(1))  # 抹消区分
    MENKYOKOFU_NENGAPPI = Column(String(8))  # 免許交付年月日
    MASSHO_NENGAPPI = Column(String(8))  # 抹消年月日

    # 騎手基本情報
    SEINENGAPPI = Column(String(8))  # 生年月日
    KISHUMEI = Column(String(34))  # 騎手名
    KISHUMEI_KANA = Column(String(30))  # 騎手名カナ
    KISHUMEI_RYAKUSHO = Column(String(8))  # 騎手名略称
    KISHUMEI_ENG = Column(String(80))  # 騎手名英語
    SEIBETSU_CODE = Column(String(1))  # 性別コード

    # 資格・所属
    KIJO_SHIKAKU_CODE = Column(String(1))  # 騎乗資格コード
    KISHU_MINARAI_CODE = Column(String(1))  # 騎手見習いコード
    TOZAI_SHOZOKU_CODE = Column(String(1))  # 東西所属コード

    # テーブル設定
    __table_args__ = (
        Index('idx_kishu_name', 'KISHUMEI'),
        Index('idx_kishu_tozai', 'TOZAI_SHOZOKU_CODE'),
    )


class ChokyoshiMaster(Base):
    """CHOKYOSHI_MASTER - 調教師マスター"""

    __tablename__ = "CHOKYOSHI_MASTER"

    # メタ情報
    INSERT_TIMESTAMP = Column(String(19))
    UPDATE_TIMESTAMP = Column(String(19))
    RECORD_SHUBETSU_ID = Column(String(2))
    DATA_KUBUN = Column(String(1))
    DATA_SAKUSEI_NENGAPPI = Column(String(8))

    # プライマリキー
    CHOKYOSHI_CODE = Column(String(5), primary_key=True, nullable=False)

    # 削除・登録情報
    MASSHO_KUBUN = Column(String(1))  # 抹消区分
    MENKYOKOFU_NENGAPPI = Column(String(8))  # 免許交付年月日
    MASSHO_NENGAPPI = Column(String(8))  # 抹消年月日

    # 調教師基本情報
    SEINENGAPPI = Column(String(8))  # 生年月日
    CHOKYOSHIMEI = Column(String(34))  # 調教師名
    CHOKYOSHIMEI_KANA = Column(String(30))  # 調教師名カナ
    CHOKYOSHIMEI_RYAKUSHO = Column(String(8))  # 調教師名略称
    CHOKYOSHIMEI_ENG = Column(String(80))  # 調教師名英語
    SEIBETSU_CODE = Column(String(1))  # 性別コード

    # 所属
    TOZAI_SHOZOKU_CODE = Column(String(1))  # 東西所属コード

    # テーブル設定
    __table_args__ = (
        Index('idx_chokyo_name', 'CHOKYOSHIMEI'),
        Index('idx_chokyo_tozai', 'TOZAI_SHOZOKU_CODE'),
    )


class BanushiMaster(Base):
    """BANUSHI_MASTER - 馬主マスター"""

    __tablename__ = "BANUSHI_MASTER"

    # メタ情報
    INSERT_TIMESTAMP = Column(String(19))
    UPDATE_TIMESTAMP = Column(String(19))
    RECORD_SHUBETSU_ID = Column(String(2))
    DATA_KUBUN = Column(String(1))
    DATA_SAKUSEI_NENGAPPI = Column(String(8))

    # プライマリキー
    BANUSHI_CODE = Column(String(6), primary_key=True, nullable=False)

    # 馬主情報
    BANUSHIMEI = Column(String(64))  # 馬主名
    BANUSHIMEI_KANA = Column(String(100))  # 馬主名カナ
    BANUSHIMEI_ENG = Column(String(100))  # 馬主名英語
    HOJIN_KUBUN = Column(String(1))  # 法人区分

    # テーブル設定
    __table_args__ = (
        Index('idx_banushi_name', 'BANUSHIMEI'),
    )


# 互換性のためのエイリアス（段階的移行用）
NRace = RaceShosai
NUma = KyosobaMaster2
NUmaRace = UmagotoRaceJoho
NKisyu = KishuMaster
NChokyo = ChokyoshiMaster
NBanusi = BanushiMaster
