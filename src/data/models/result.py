"""
レース結果関連モデル定義

出走情報とレース結果のモデルを定義
"""
from sqlalchemy import (
    Column,
    Decimal,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class RaceEntry(BaseModel):
    """出走情報モデル"""

    __tablename__ = "race_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    race_id = Column(
        Integer,
        ForeignKey("races.id", ondelete="CASCADE"),
        nullable=False,
        comment="レースID",
    )
    horse_id = Column(
        Integer,
        ForeignKey("horses.id", ondelete="CASCADE"),
        nullable=False,
        comment="馬ID",
    )
    post_position = Column(Integer, nullable=False, comment="枠番")
    horse_number = Column(Integer, nullable=False, comment="馬番")
    jockey_id = Column(
        Integer,
        ForeignKey("jockeys.id", ondelete="RESTRICT"),
        nullable=False,
        comment="騎手ID",
    )
    trainer_id = Column(
        Integer,
        ForeignKey("trainers.id", ondelete="RESTRICT"),
        comment="調教師ID",
    )
    weight_carried = Column(Decimal(4, 1), nullable=False, comment="斤量")
    horse_weight = Column(Integer, comment="馬体重")
    horse_weight_diff = Column(Integer, comment="馬体重増減")
    age = Column(Integer, nullable=False, comment="年齢")
    odds_win = Column(Decimal(6, 1), comment="単勝オッズ")
    odds_place_min = Column(Decimal(6, 1), comment="複勝オッズ（最小）")
    odds_place_max = Column(Decimal(6, 1), comment="複勝オッズ（最大）")
    popularity = Column(Integer, comment="人気順位")

    # リレーション
    race = relationship("Race", back_populates="entries")
    horse = relationship("Horse", back_populates="race_entries")
    jockey = relationship("Jockey", back_populates="race_entries")
    trainer = relationship("Trainer", back_populates="race_entries")
    result = relationship(
        "RaceResult", back_populates="entry", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("race_id", "horse_number", name="unique_race_horse"),
        Index("idx_horse_id", "horse_id"),
        Index("idx_jockey_id", "jockey_id"),
    )


class RaceResult(BaseModel):
    """レース結果モデル"""

    __tablename__ = "race_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    race_entry_id = Column(
        Integer,
        ForeignKey("race_entries.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="出走情報ID",
    )
    finish_position = Column(Integer, comment="着順")
    finish_time = Column(Time, comment="タイム")
    last_3f_time = Column(Decimal(4, 1), comment="上がり3ハロン")
    corner_positions = Column(String(20), comment="通過順位")
    remarks = Column(Text, comment="備考")
    prize_money = Column(Integer, comment="獲得賞金")

    # リレーション
    entry = relationship("RaceEntry", back_populates="result")

    __table_args__ = (Index("idx_finish_position", "finish_position"),)