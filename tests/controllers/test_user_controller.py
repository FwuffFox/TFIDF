import pytest
from fastapi.encoders import jsonable_encoder

from app.controllers.utils.responses import response403


async def login(client, user_data):
    """
    Helper function to log in a user and return the response. Stores access token in the client for further requests.
    """
    response = await client.post(
        "/user/login",
        data={
            "username": user_data["username"],
            "password": user_data["password"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    client.access_token = response.json()["access_token"]
    return response


class TestUserController:
    @pytest.fixture(scope="class")
    def user_data(self):
        return {
            "username": "testuser",
            "password": "testpassword",
            "email": "testemail",
        }

    async def test_register_user(self, client, user_data):
        response = await client.post("/user/register", json=user_data)
        assert response.status_code == 200
        assert response.json() == {"status": "registered"}

    async def test_login_user(self, client, user_data):
        response = await login(client, user_data)
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "token_type" in response.json()
        

    async def test_get_current_user(self, client, user_data):
        if not hasattr(client, "access_token"):
            pytest.skip("Access token not available. Skipping test_get_current_user.")

        response = await client.get(
            "/user/me", headers={"Authorization": f"Bearer {client.access_token}"}
        )
        assert response.status_code == 200
        user_data = response.json()
        assert user_data["username"] == "testuser"
        assert user_data["email"] == "testemail"

    async def test_register_existing_user(self, client, user_data):
        # Attempt to register the same user again
        response = await client.post("/user/register", json=user_data)
        assert response.status_code == 400
        assert response.json() == {"detail": "Username already exists"}

    async def test_login_invalid_user(self, client):
        # Attempt to login with invalid credentials
        response = await client.post(
            "/user/login",
            data={"username": "invaliduser", "password": "invalidpassword"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid username or password"}

    async def test_get_current_user_unauthenticated(self, client):
        # Attempt to get current user without authentication
        response = await client.get("/user/me")
        assert response.status_code == 401
        assert response.json() == {"detail": "Not authenticated"}

    async def test_logout_user(self, client):
        if not hasattr(client, "access_token"):
            pytest.skip("Access token not available. Skipping test_logout_user.")

        response = await client.post(
            "/user/logout", headers={"Authorization": f"Bearer {client.access_token}"}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "logged out successfully"}

        # Verify that the access token is now invalid
        response = await client.get(
            "/user/me", headers={"Authorization": f"Bearer {client.access_token}"}
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "Could not validate credentials"}

    async def test_change_password(self, client, user_data):
        response = await login(client, user_data)

        # Change password
        response = await client.patch(
            "/user/",
            json={
                "old_password": user_data["password"],
                "new_password": "newpassword",
            },
            headers={"Authorization": f"Bearer {client.access_token}"},
        )
        assert response.status_code == 200
        
        assert response.json() == {"status": "password changed, all sessions invalidated"}
        
        # verify logged out
        response = await client.get(
            "/user/me", headers={"Authorization": f"Bearer {client.access_token}"}
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "Could not validate credentials"}

        # Verify that the new password works
        response = await client.post(
            "/user/login",
            data={"username": user_data["username"], "password": "newpassword"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()