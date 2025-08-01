"""
レース関連モデル定義

レース情報と競馬場情報のモデルを定義
"""
from sqlalchemy import (
    JSON,
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class Racecourse(BaseModel):
    """競馬場マスタモデル"""

    __tablename__ = "racecourses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    jra_code = Column(String(2), unique=True, nullable=False, comment="JRAコード")
    name = Column(String(50), nullable=False, comment="競馬場名")
    name_kana = Column(String(100), comment="競馬場名（カナ）")
    location = Column(String(100), comment="所在地")

    # リレーション
    races = relationship("Race", back_populates="racecourse")


class Race(BaseModel):
    """レース情報モデル"""

    __tablename__ = "races"

    id = Column(Integer, primary_key=True, autoincrement=True)
    race_key = Column(
        String(20), unique=True, nullable=False, comment="レースキー (YYYYMMDDRRNN)"
    )
    race_date = Column(Date, nullable=False, comment="開催日")
    racecourse_id = Column(
        Integer, ForeignKey("racecourses.id"), comment="競馬場ID"
    )
    race_number = Column(Integer, nullable=False, comment="R数")
    race_name = Column(String(100), nullable=False, comment="レース名")
    race_name_sub = Column(String(100), comment="レース名（サブ）")
    grade = Column(String(10), comment="グレード (G1, G2, G3, OP, etc)")
    race_type = Column(String(10), nullable=False, comment="トラックタイプ (芝/ダート)")
    distance = Column(Integer, nullable=False, comment="距離（メートル）")
    direction = Column(String(10), comment="回り (右/左/直線)")
    weather = Column(String(10), comment="天候")
    track_condition = Column(String(10), comment="馬場状態")
    prize_money = Column(JSON, comment="賞金情報（JSON形式）")
    entry_count = Column(Integer, comment="出走頭数")

    # リレーション
    racecourse = relationship("Racecourse", back_populates="races")
    entries = relationship("RaceEntry", back_populates="race", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="race", cascade="all, delete-orphan")
    odds_history = relationship("OddsHistory", back_populates="race", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_race_date", "race_date"),
        Index("idx_racecourse_id", "racecourse_id"),
        Index("idx_grade", "grade"),
    )