"""
予測関連のスキーマ定義
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, validator


class RaceType(str, Enum):
    """レースタイプ"""

    TURF = "turf"  # 芝
    DIRT = "dirt"  # ダート
    OBSTACLE = "obstacle"  # 障害


class RaceGrade(str, Enum):
    """レースグレード"""

    G1 = "G1"
    G2 = "G2"
    G3 = "G3"
    OPEN = "OPEN"
    LISTED = "L"
    NEWCOMER = "新馬"
    UNGRADED = "未勝利"
    ONE_WIN = "1勝クラス"
    TWO_WIN = "2勝クラス"
    THREE_WIN = "3勝クラス"


class WeatherCondition(str, Enum):
    """天候"""

    FINE = "晴"
    CLOUDY = "曇"
    RAINY = "雨"
    SNOWY = "雪"
    FOGGY = "霧"


class TrackCondition(str, Enum):
    """馬場状態"""

    FIRM = "良"
    GOOD = "稍重"
    YIELDING = "重"
    SOFT = "不良"


class HorseInfo(BaseModel):
    """馬情報"""

    horse_id: str = Field(..., description="馬ID")
    name: str = Field(..., description="馬名")
    age: int = Field(..., ge=2, le=10, description="年齢")
    sex: str = Field(..., pattern="^(牡|牝|セ)$", description="性別")
    weight: Optional[float] = Field(None, ge=300, le=700, description="馬体重")
    weight_change: Optional[int] = Field(None, ge=-50, le=50, description="馬体重増減")
    post_position: int = Field(..., ge=1, le=18, description="枠番")
    horse_number: int = Field(..., ge=1, le=18, description="馬番")
    jockey_name: str = Field(..., description="騎手名")
    jockey_weight: float = Field(..., ge=45, le=65, description="斤量")
    trainer_name: str = Field(..., description="調教師名")
    owner_name: Optional[str] = Field(None, description="馬主名")
    odds: Optional[float] = Field(None, ge=1.0, description="オッズ")
    popularity: Optional[int] = Field(None, ge=1, le=18, description="人気順")


class RaceInfo(BaseModel):
    """レース情報"""

    race_id: str = Field(..., description="レースID")
    race_date: date = Field(..., description="開催日")
    race_number: int = Field(..., ge=1, le=12, description="レース番号")
    race_name: str = Field(..., description="レース名")
    track: str = Field(..., description="競馬場")
    race_type: RaceType = Field(..., description="レースタイプ")
    distance: int = Field(..., ge=800, le=3600, description="距離（メートル）")
    race_grade: RaceGrade | None = Field(None, description="レースグレード")
    weather: WeatherCondition | None = Field(None, description="天候")
    track_condition: TrackCondition | None = Field(None, description="馬場状態")
    prize_money: Optional[int] = Field(None, ge=0, description="賞金総額")
    field_size: int = Field(..., ge=2, le=18, description="出走頭数")


class PredictionRequest(BaseModel):
    """予測リクエスト"""

    race_info: RaceInfo = Field(..., description="レース情報")
    horses: list[HorseInfo] = Field(
        ..., min_items=2, max_items=18, description="出走馬情報"
    )
    include_confidence: bool = Field(default=True, description="信頼度を含める")
    include_features: bool = Field(default=False, description="特徴量を含める")

    @validator("horses")
    def validate_horses(cls, v, values):
        """出走馬の検証"""
        if "race_info" in values:
            if len(v) != values["race_info"].field_size:
                raise ValueError(
                    f"出走頭数が一致しません。期待: {values['race_info'].field_size}, 実際: {len(v)}"
                )

        # 馬番の重複チェック
        horse_numbers = [h.horse_number for h in v]
        if len(horse_numbers) != len(set(horse_numbers)):
            raise ValueError("馬番が重複しています")

        return v


class PredictionResult(BaseModel):
    """予測結果（個別馬）"""

    horse_id: str = Field(..., description="馬ID")
    horse_name: str = Field(..., description="馬名")
    horse_number: int = Field(..., description="馬番")
    win_probability: float = Field(..., ge=0, le=1, description="勝率")
    place_probability: float = Field(..., ge=0, le=1, description="複勝率")
    predicted_rank: int = Field(..., ge=1, le=18, description="予測順位")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="予測信頼度")
    expected_value: Optional[float] = Field(None, description="期待値")
    features: dict[str, Any] | None = Field(None, description="使用した特徴量")


class RacePredictionResponse(BaseModel):
    """レース予測レスポンス"""

    race_id: str = Field(..., description="レースID")
    race_name: str = Field(..., description="レース名")
    prediction_id: str = Field(..., description="予測ID")
    predicted_at: datetime = Field(..., description="予測実行日時")
    model_version: str = Field(..., description="モデルバージョン")
    predictions: list[PredictionResult] = Field(..., description="予測結果リスト")
    recommended_bets: dict[str, list[int]] | None = Field(None, description="推奨馬券")
    metadata: dict[str, Any] | None = Field(None, description="メタデータ")

    class Config:
        schema_extra = {
            "example": {
                "race_id": "202312010101",
                "race_name": "有馬記念",
                "prediction_id": "pred_20231201_001",
                "predicted_at": "2023-12-01T10:00:00",
                "model_version": "v1.0.0",
                "predictions": [
                    {
                        "horse_id": "2021104321",
                        "horse_name": "エフフォーリア",
                        "horse_number": 1,
                        "win_probability": 0.25,
                        "place_probability": 0.65,
                        "predicted_rank": 1,
                        "confidence_score": 0.85,
                        "expected_value": 3.2,
                    }
                ],
                "recommended_bets": {
                    "win": [1],
                    "place": [1, 3, 5],
                    "exacta": [1, 3],
                    "trio": [1, 3, 5],
                },
            }
        }


class BatchPredictionRequest(BaseModel):
    """バッチ予測リクエスト"""

    races: list[PredictionRequest] = Field(
        ..., min_items=1, max_items=100, description="予測対象レースリスト"
    )
    priority: Optional[str] = Field(
        default="normal", pattern="^(high|normal|low)$", description="処理優先度"
    )
    callback_url: Optional[str] = Field(None, description="結果通知用URL")


class BatchPredictionResponse(BaseModel):
    """バッチ予測レスポンス"""

    batch_id: str = Field(..., description="バッチID")
    status: str = Field(..., description="処理ステータス")
    total_races: int = Field(..., description="総レース数")
    completed_races: int = Field(default=0, description="完了レース数")
    created_at: datetime = Field(..., description="作成日時")
    estimated_completion: datetime | None = Field(None, description="完了予定時刻")
    results_url: Optional[str] = Field(None, description="結果取得URL")


class PredictionHistory(BaseModel):
    """予測履歴"""

    prediction_id: str
    race_id: str
    race_name: str
    race_date: date
    predicted_at: datetime
    model_version: str
    accuracy_score: Optional[float] = None
    actual_results: dict[str, Any] | None = None

    class Config:
        orm_mode = True
