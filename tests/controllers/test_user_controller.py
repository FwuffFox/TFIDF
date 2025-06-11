import pytest
from fastapi.encoders import jsonable_encoder

class TestUserController:
    @pytest.fixture(scope="class")
    def user_data(self):
        return {
            "username": "testuser",
            "password": "testpassword",
            "email": "testemail"
        }
    
    def test_register_user(self, client, user_data):
        response = client.post("/user/register", json=user_data)
        assert response.status_code == 200
        assert response.json() == {"status": "registered"}

    def test_login_user(self, client, user_data):
        # For login, we need to use form data in the format expected by OAuth2PasswordRequestForm
        response = client.post(
            "/user/login",
            data={
                "username": user_data["username"],
                "password": user_data["password"]
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "token_type" in response.json()
        
        # Store the access token for further tests
        client.access_token = response.json()["access_token"]
        
    def test_get_current_user(self, client, user_data):
        if not hasattr(client, 'access_token'):
            pytest.skip("Access token not available. Skipping test_get_current_user.")
        
        response = client.get(
            "/user/me",
            headers={"Authorization": f"Bearer {client.access_token}"}
        )
        assert response.status_code == 200
        user_data = response.json()
        assert user_data["username"] == "testuser"
        assert user_data["email"] == "testemail"
        
    def test_register_existing_user(self, client, user_data):
        # Attempt to register the same user again
        response = client.post("/user/register", json=user_data)
        assert response.status_code == 400
        assert response.json() == {"detail": "Username already exists"}
        
    def test_login_invalid_user(self, client):
        # Attempt to login with invalid credentials
        response = client.post(
            "/user/login",
            data={
                "username": "invaliduser",
                "password": "invalidpassword"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid username or password"}
        
    def test_get_current_user_unauthenticated(self, client):
        # Attempt to get current user without authentication
        response = client.get("/user/me")
        assert response.status_code == 401
        assert response.json() == {"detail": "Not authenticated"}