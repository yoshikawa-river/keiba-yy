#!/usr/bin/env python
"""
API動作確認スクリプト
"""

import sys
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_endpoint(name, method, path, **kwargs):
    """エンドポイントをテストする"""
    try:
        if method == "GET":
            response = client.get(path, **kwargs)
        elif method == "POST":
            response = client.post(path, **kwargs)
        else:
            response = client.request(method, path, **kwargs)

        status = "✓" if response.status_code < 400 else "✗"
        print(f"{status} {name:30} {method:6} {path:30} -> {response.status_code}")

        if response.status_code >= 400 and response.status_code < 500:
            try:
                body = response.json()
                if "detail" in body:
                    print(f"  Detail: {body['detail']}")
            except:
                pass

        return response.status_code < 400
    except Exception as e:
        print(f"✗ {name:30} {method:6} {path:30} -> ERROR: {e}")
        return False


def main():
    print("=" * 80)
    print("競馬AI API 動作確認レポート")
    print("=" * 80)
    print()

    results = []

    # 基本エンドポイント
    print("【基本エンドポイント】")
    results.append(test_endpoint("ルート", "GET", "/"))
    results.append(test_endpoint("ヘルスチェック", "GET", "/health"))
    results.append(test_endpoint("メトリクス", "GET", "/metrics"))
    results.append(test_endpoint("OpenAPI スキーマ", "GET", "/openapi.json"))
    results.append(test_endpoint("ドキュメント", "GET", "/docs"))
    results.append(test_endpoint("ReDoc", "GET", "/redoc"))
    print()

    # 認証エンドポイント
    print("【認証エンドポイント】")

    # ユーザー登録
    register_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User",
    }
    results.append(
        test_endpoint("ユーザー登録", "POST", "/api/v1/auth/register", json=register_data)
    )

    # ログイン
    login_data = {"username": "testuser", "password": "TestPassword123!"}
    results.append(test_endpoint("ログイン", "POST", "/api/v1/auth/login", data=login_data))

    # 認証なしでのアクセス
    results.append(test_endpoint("現在のユーザー取得（認証なし）", "GET", "/api/v1/auth/me"))
    print()

    # 予測エンドポイント（認証なし）
    print("【予測エンドポイント（認証なし）】")

    # 単一レース予測
    prediction_data = {
        "race_info": {
            "race_id": "2023120101",
            "race_name": "テストレース",
            "race_date": "2023-12-01",
            "track": "東京",
            "distance": 1600,
            "race_type": "turf",
            "field_size": 10,
        },
        "horses": [
            {
                "horse_id": "horse001",
                "name": "テストホース1",
                "horse_number": 1,
                "jockey": "テスト騎手1",
                "trainer": "テスト調教師1",
                "weight": 500,
                "age": 3,
                "sex": "male",
                "odds": 5.2,
            },
            {
                "horse_id": "horse002",
                "name": "テストホース2",
                "horse_number": 2,
                "jockey": "テスト騎手2",
                "trainer": "テスト調教師2",
                "weight": 498,
                "age": 4,
                "sex": "female",
                "odds": 12.5,
            },
        ],
    }
    results.append(
        test_endpoint(
            "レース予測（認証なし）", "POST", "/api/v1/predictions/race", json=prediction_data
        )
    )

    # バッチ予測
    batch_data = {"races": [prediction_data]}
    results.append(
        test_endpoint(
            "バッチ予測（認証なし）", "POST", "/api/v1/predictions/batch", json=batch_data
        )
    )

    # 予測履歴
    results.append(test_endpoint("予測履歴（認証なし）", "GET", "/api/v1/predictions/history"))

    # モデル一覧
    results.append(test_endpoint("モデル一覧（認証なし）", "GET", "/api/v1/predictions/models"))
    print()

    # デバッグエンドポイント
    print("【デバッグエンドポイント】")
    results.append(test_endpoint("ルート一覧", "GET", "/debug/routes"))
    results.append(test_endpoint("WebSocket統計", "GET", "/debug/websocket-stats"))
    print()

    # 結果サマリー
    print("=" * 80)
    print("【テスト結果サマリー】")
    passed = sum(results)
    total = len(results)
    print(f"成功: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("✅ すべてのエンドポイントが正常に動作しています")
    else:
        print(f"⚠️ {total - passed}個のエンドポイントで問題が検出されました")

    print("=" * 80)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
