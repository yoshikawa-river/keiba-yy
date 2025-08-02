"""
ベースモデル定義

全てのモデルが継承する基底クラスを定義
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime
from sqlalchemy.ext.declarative import declarative_base

if TYPE_CHECKING:
    from sqlalchemy.ext.declarative import DeclarativeMeta

    Base: DeclarativeMeta = declarative_base()
else:
    Base = declarative_base()


class BaseModel(Base):
    """ベースモデル（共通カラム）"""

    __abstract__ = True

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self):
        """モデルを辞書形式に変換"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self):
        """モデルの文字列表現"""
        class_name = self.__class__.__name__
        attrs = ", ".join([f"{k}={v}" for k, v in self.to_dict().items()])
        return f"<{class_name}({attrs})>"
