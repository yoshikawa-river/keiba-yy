"""
予測APIのテスト
"""

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies.auth import (
    get_api_key,
    get_optional_user,
    rate_limit_100,
    require_api_key,
)
from src.api.main import app

client = TestClient(app)


# テスト用のAPIキー依存関数
async def mock_require_api_key() -> str:
    """テスト用のモックAPIキー依存関数"""
    return "sk_test_api_key_1234567890123456789012345"


# テスト用のレート制限依存関数
async def mock_rate_limit() -> bool:
    """テスト用のモックレート制限依存関数"""
    return True


# テスト用のAPIキー取得依存関数
async def mock_get_api_key() -> str:
    """テスト用のモックAPIキー取得依存関数"""
    return "sk_test_api_key_1234567890123456789012345"


# テスト用のオプショナルユーザー依存関数
async def mock_get_optional_user():
    """テスト用のモックオプショナルユーザー依存関数"""


# テスト時に依存関数をオーバーライド
app.dependency_overrides[require_api_key] = mock_require_api_key
app.dependency_overrides[rate_limit_100] = mock_rate_limit
app.dependency_overrides[get_api_key] = mock_get_api_key
app.dependency_overrides[get_optional_user] = mock_get_optional_user


class TestPredictionAPI:
    """予測APIテストクラス"""

    @pytest.fixture
    def api_key(self):
        """テスト用APIキー"""
        # 実際のテストではモックAPIキーを使用（35文字以上の長さが必要）
        return "sk_test_api_key_1234567890123456789012345"

    @pytest.fixture
    def race_request_data(self):
        """テスト用レースリクエストデータ"""
        return {
            "race_info": {
                "race_id": "202312010101",
                "race_date": "2023-12-01",
                "race_number": 1,
                "race_name": "テストレース",
                "track": "東京",
                "race_type": "turf",
                "distance": 2000,
                "race_grade": "G1",
                "weather": "晴",
                "track_condition": "良",
                "prize_money": 100000000,
                "field_size": 3,
            },
            "horses": [
                {
                    "horse_id": "2021104321",
                    "name": "テストホース1",
                    "age": 3,
                    "sex": "牡",
                    "weight": 480.0,
                    "weight_change": 2,
                    "post_position": 1,
                    "horse_number": 1,
                    "jockey_name": "テスト騎手1",
                    "jockey_weight": 55.0,
                    "trainer_name": "テスト調教師1",
                    "odds": 2.5,
                    "popularity": 1,
                },
                {
                    "horse_id": "2021104322",
                    "name": "テストホース2",
                    "age": 4,
                    "sex": "牝",
                    "weight": 460.0,
                    "weight_change": -2,
                    "post_position": 2,
                    "horse_number": 2,
                    "jockey_name": "テスト騎手2",
                    "jockey_weight": 54.0,
                    "trainer_name": "テスト調教師2",
                    "odds": 5.0,
                    "popularity": 2,
                },
                {
                    "horse_id": "2021104323",
                    "name": "テストホース3",
                    "age": 3,
                    "sex": "セ",
                    "weight": 490.0,
                    "weight_change": 0,
                    "post_position": 3,
                    "horse_number": 3,
                    "jockey_name": "テスト騎手3",
                    "jockey_weight": 56.0,
                    "trainer_name": "テスト調教師3",
                    "odds": 10.0,
                    "popularity": 3,
                },
            ],
            "include_confidence": True,
            "include_features": False,
        }

    def test_predict_race_with_api_key(self, api_key, race_request_data):
        """APIキーを使用したレース予測テスト"""
        response = client.post(
            "/api/v1/predictions/race",
            json=race_request_data,
        )

        # モックAPIキーで認証が通るため200を期待
        assert response.status_code == 200

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert data["data"]["race_id"] == "202312010101"
            assert len(data["data"]["predictions"]) == 3

    def test_predict_race_validation_error(self, api_key):
        """バリデーションエラーテスト"""
        invalid_data = {
            "race_info": {
                "race_id": "202312010101",
                "race_date": "2023-12-01",
                "race_number": 99,  # 無効な値
                "race_name": "テストレース",
                "track": "東京",
                "race_type": "invalid_type",  # 無効な値
                "distance": 100,  # 範囲外
                "field_size": 2,
            },
            "horses": [],  # 空のリスト
        }

        response = client.post(
            "/api/v1/predictions/race",
            json=invalid_data,
        )
        assert response.status_code == 422

    def test_batch_prediction(self, api_key, race_request_data):
        """バッチ予測テスト"""
        batch_data = {
            "races": [race_request_data, race_request_data],
            "priority": "normal",
        }

        response = client.post("/api/v1/predictions/batch", json=batch_data)

        # モック認証で成功を期待
        assert response.status_code == 200

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "batch_id" in data["data"]
            assert data["data"]["total_races"] == 2

    def test_get_prediction_history(self, api_key):
        """予測履歴取得テスト"""
        response = client.get(
            "/api/v1/predictions/history",
            params={"page": 1, "size": 10},
        )

        assert response.status_code == 200

        if response.status_code == 200:
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert "page" in data

    def test_get_available_models(self, api_key):
        """利用可能モデル一覧取得テスト"""
        response = client.get("/api/v1/predictions/models")

        assert response.status_code == 200

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert isinstance(data["data"], list)

            if len(data["data"]) > 0:
                model = data["data"][0]
                assert "model_id" in model
                assert "name" in model
                assert "version" in model

    def test_horse_number_validation(self, api_key):
        """馬番重複バリデーションテスト"""
        data = {
            "race_info": {
                "race_id": "202312010101",
                "race_date": "2023-12-01",
                "race_number": 1,
                "race_name": "テストレース",
                "track": "東京",
                "race_type": "turf",
                "distance": 2000,
                "field_size": 2,
            },
            "horses": [
                {
                    "horse_id": "001",
                    "name": "馬1",
                    "age": 3,
                    "sex": "牡",
                    "post_position": 1,
                    "horse_number": 1,  # 同じ馬番
                    "jockey_name": "騎手1",
                    "jockey_weight": 55.0,
                    "trainer_name": "調教師1",
                },
                {
                    "horse_id": "002",
                    "name": "馬2",
                    "age": 3,
                    "sex": "牡",
                    "post_position": 2,
                    "horse_number": 1,  # 同じ馬番（エラー）
                    "jockey_name": "騎手2",
                    "jockey_weight": 55.0,
                    "trainer_name": "調教師2",
                },
            ],
        }

        response = client.post("/api/v1/predictions/race", json=data)
        assert response.status_code == 422
