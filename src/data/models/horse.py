"""
馬・騎手・調教師関連モデル定義

競走馬、騎手、調教師のマスタ情報モデルを定義
"""
from sqlalchemy import (
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class Horse(BaseModel):
    """馬情報モデル"""

    __tablename__ = "horses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    horse_id = Column(String(10), unique=True, nullable=False, comment="馬ID")
    name = Column(String(50), nullable=False, comment="馬名")
    name_kana = Column(String(100), comment="馬名（カナ）")
    sex = Column(String(10), nullable=False, comment="性別 (牡/牝/セ)")
    birth_date = Column(Date, comment="生年月日")
    color = Column(String(20), comment="毛色")
    father_name = Column(String(50), comment="父馬名")
    mother_name = Column(String(50), comment="母馬名")
    mother_father_name = Column(String(50), comment="母父馬名")
    owner_name = Column(String(100), comment="馬主名")
    trainer_name = Column(String(50), comment="調教師名")
    breeding_farm = Column(String(100), comment="生産牧場")

    # リレーション
    race_entries = relationship("RaceEntry", back_populates="horse")
    feature_cache = relationship("FeatureCache", back_populates="horse")

    __table_args__ = (
        Index("idx_name", "name"),
        Index("idx_name_fulltext", "name"),  # MySQLのFULLTEXTインデックス
    )


class Jockey(BaseModel):
    """騎手マスタモデル"""

    __tablename__ = "jockeys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    jockey_id = Column(String(10), unique=True, nullable=False, comment="騎手ID")
    name = Column(String(50), nullable=False, comment="騎手名")
    name_kana = Column(String(100), comment="騎手名（カナ）")
    birth_date = Column(Date, comment="生年月日")
    license_date = Column(Date, comment="免許取得日")

    # リレーション
    race_entries = relationship("RaceEntry", back_populates="jockey")


class Trainer(BaseModel):
    """調教師マスタモデル"""

    __tablename__ = "trainers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trainer_id = Column(String(10), unique=True, nullable=False, comment="調教師ID")
    name = Column(String(50), nullable=False, comment="調教師名")
    name_kana = Column(String(100), comment="調教師名（カナ）")
    belonging = Column(String(20), comment="所属 (美浦/栗東)")

    # リレーション
    race_entries = relationship("RaceEntry", back_populates="trainer")