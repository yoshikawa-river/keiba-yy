"""
メインAPIのテスト
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestMainAPI:
    """メインAPIテストクラス"""

    def test_root_endpoint(self):
        """ルートエンドポイントテスト"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert data["docs"] == "/docs"

    def test_health_check(self):
        """ヘルスチェックテスト"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "version" in data
        assert "timestamp" in data
        assert "uptime" in data
        assert "services" in data

        # サービスステータス確認
        services = data["services"]
        assert "api" in services
        assert services["api"] is True

    def test_metrics_endpoint(self):
        """メトリクスエンドポイントテスト"""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "uptime_seconds" in data
        assert "websocket_connections" in data
        assert "api_version" in data

    def test_openapi_schema(self):
        """OpenAPIスキーマテスト"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "競馬予想AIシステム"

    def test_404_error(self):
        """404エラーテスト"""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    def test_cors_headers(self):
        """CORSヘッダーテスト"""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_request_id_header(self):
        """リクエストIDヘッダーテスト"""
        response = client.get("/health")
        assert response.status_code == 200
        assert "x-request-id" in response.headers
        assert "x-process-time" in response.headers

    def test_rate_limit_headers(self):
        """レート制限ヘッダーテスト"""
        response = client.get("/health")
        assert response.status_code == 200
        # レート制限が有効な場合のみヘッダーが存在
        if "x-ratelimit-limit" in response.headers:
            assert "x-ratelimit-remaining" in response.headers
            assert "x-ratelimit-reset" in response.headers

    @pytest.mark.parametrize("endpoint", ["/docs", "/redoc"])
    def test_documentation_endpoints(self, endpoint):
        """ドキュメントエンドポイントテスト"""
        response = client.get(endpoint)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestErrorHandling:
    """エラーハンドリングテスト"""

    def test_validation_error_format(self):
        """バリデーションエラーのフォーマットテスト"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "a",  # 短すぎる
                "email": "invalid-email",  # 無効なメール
                "password": "weak",  # 弱いパスワード
            },
        )
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "details" in data
        assert isinstance(data["details"], list)

    def test_http_exception_format(self):
        """HTTP例外のフォーマットテスト"""
        response = client.get("/api/v1/auth/me")  # 認証なし
        assert response.status_code == 403  # Security schemeのため403
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "request_id" in data


class TestDebugEndpoints:
    """デバッグエンドポイントテスト（開発環境のみ）"""

    def test_debug_routes(self):
        """ルート一覧取得テスト"""
        # デバッグモードでのみ存在
        from src.api.config import settings

        if settings.debug:
            response = client.get("/debug/routes")
            assert response.status_code == 200
            data = response.json()
            assert "routes" in data
            assert isinstance(data["routes"], list)

    def test_debug_websocket_stats(self):
        """WebSocket統計取得テスト"""
        from src.api.config import settings

        if settings.debug:
            response = client.get("/debug/websocket-stats")
            assert response.status_code == 200
            data = response.json()
            assert "total_connections" in data
            assert "unique_users" in data
            assert "channels" in data
