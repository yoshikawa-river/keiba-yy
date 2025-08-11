"""
認証APIのテスト
"""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestAuthAPI:
    """認証APIテストクラス"""

    def test_register_user(self):
        """ユーザー登録テスト"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser123",
                "email": "test123@example.com",
                "password": "Test123!@#",
                "full_name": "Test User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["username"] == "testuser123"
        assert data["data"]["email"] == "test123@example.com"

    def test_register_duplicate_user(self):
        """重複ユーザー登録テスト"""
        # 既存のユーザー名で登録試行
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "another@example.com",
                "password": "Test123!@#",
            },
        )
        assert response.status_code == 400

    def test_register_weak_password(self):
        """弱いパスワードでの登録テスト"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "weakpassuser",
                "email": "weak@example.com",
                "password": "weak",  # 弱いパスワード
            },
        )
        assert response.status_code == 422

    def test_login_success(self):
        """ログイン成功テスト"""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "Test123!@#"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self):
        """無効な認証情報でのログインテスト"""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_custom_endpoint(self):
        """カスタムログインエンドポイントテスト"""
        response = client.post(
            "/api/v1/auth/login/custom",
            json={"username": "testuser", "password": "Test123!@#"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_get_current_user(self):
        """現在のユーザー情報取得テスト"""
        # ログインしてトークン取得
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "Test123!@#"},
        )
        token = login_response.json()["access_token"]

        # ユーザー情報取得
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["username"] == "testuser"

    def test_get_current_user_invalid_token(self):
        """無効なトークンでのユーザー情報取得テスト"""
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    def test_refresh_token(self):
        """トークンリフレッシュテスト"""
        # ログインしてトークン取得
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "Test123!@#"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # トークンリフレッシュ
        response = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_create_api_key(self):
        """APIキー作成テスト"""
        # ログインしてトークン取得
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "Test123!@#"},
        )
        token = login_response.json()["access_token"]

        # APIキー作成
        response = client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Test API Key"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test API Key"
        assert data["data"]["key"].startswith("sk_")
