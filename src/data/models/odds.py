"""
オッズ・予測関連モデル定義

オッズ履歴、予測結果、特徴量キャッシュのモデルを定義
"""

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class OddsHistory(BaseModel):
    """オッズ履歴モデル"""

    __tablename__ = "odds_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    race_id = Column(
        Integer,
        ForeignKey("races.id", ondelete="CASCADE"),
        nullable=False,
        comment="レースID",
    )
    horse_number = Column(Integer, nullable=False, comment="馬番")
    odds_type = Column(
        String(20),
        nullable=False,
        comment="オッズ種別 (win/place/quinella/etc)",
    )
    odds_value = Column(Numeric(8, 1), nullable=False, comment="オッズ値")
    recorded_at = Column(DateTime, nullable=False, comment="記録日時")

    # リレーション
    race = relationship("Race", back_populates="odds_history")

    __table_args__ = (Index("idx_race_time", "race_id", "recorded_at"),)


class Prediction(BaseModel):
    """予測結果モデル"""

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    race_id = Column(
        Integer,
        ForeignKey("races.id", ondelete="CASCADE"),
        nullable=False,
        comment="レースID",
    )
    model_name = Column(String(50), nullable=False, comment="モデル名")
    model_version = Column(String(20), comment="モデルバージョン")
    prediction_data = Column(JSON, nullable=False, comment="予測結果の詳細(JSON形式)")

    # リレーション
    race = relationship("Race", back_populates="predictions")

    __table_args__ = (Index("idx_race_model", "race_id", "model_name"),)


class FeatureCache(BaseModel):
    """特徴量キャッシュモデル"""

    __tablename__ = "feature_cache"

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
    feature_type = Column(String(50), nullable=False, comment="特徴量タイプ")
    feature_data = Column(JSON, nullable=False, comment="特徴量データ(JSON形式)")
    calculated_at = Column(
        DateTime, default=DateTime, nullable=False, comment="計算日時"
    )
    expires_at = Column(DateTime, comment="有効期限")

    # リレーション
    race = relationship("Race")
    horse = relationship("Horse", back_populates="feature_cache")

    __table_args__ = (
        UniqueConstraint("race_id", "horse_id", "feature_type", name="unique_feature"),
    )
