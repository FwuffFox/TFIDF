import pytest


async def register(client, user_data):
    """
    Helper function to register a user and return the response.
    """
    response = await client.post("/user/register", json=user_data)
    return response


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
    return response


class TestUserController:
    @pytest.fixture
    def user_data(self):
        """
        Fixture to provide fresh user data for each test.
        Changed to function scope for test independence.
        """
        return {
            "username": "testuser",
            "password": "testpassword",
            "email": "testemail",
        }

    @pytest.fixture
    def alt_user_data(self):
        """
        Alternative user data for testing duplicate registrations.
        """
        return {
            "username": "altuser",
            "password": "altpassword",
            "email": "altemail",
        }

    async def test_register_user(self, client, user_data):
        """Test user registration with valid data."""
        response = await register(client, user_data)
        assert response.status_code == 200
        assert response.json() == {"status": "registered"}

    async def test_login_user(self, client, user_data):
        """Test user login with valid credentials."""
        # Register first
        reg_response = await register(client, user_data)
        assert reg_response.status_code == 200

        # Then login
        login_response = await login(client, user_data)
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()
        assert "token_type" in login_response.json()

    async def test_get_current_user(self, client, user_data):
        """Test getting current user info with valid token."""
        # Register
        await register(client, user_data)

        # Login to get token
        login_response = await login(client, user_data)
        access_token = login_response.json()["access_token"]

        # Get user info
        response = await client.get(
            "/user/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        user_info = response.json()
        assert user_info["username"] == user_data["username"]
        assert user_info["email"] == user_data["email"]

    async def test_register_existing_user(self, client, user_data):
        """Test registering a user that already exists."""
        # Register user first
        first_response = await register(client, user_data)
        assert first_response.status_code == 200

        # Attempt to register the same user again
        second_response = await register(client, user_data)
        assert second_response.status_code == 400
        assert second_response.json() == {"detail": "Username already exists"}

    async def test_login_invalid_user(self, client):
        """Test login with invalid credentials."""
        # Attempt to login with invalid credentials
        response = await client.post(
            "/user/login",
            data={"username": "invaliduser", "password": "invalidpassword"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid username or password"}

    async def test_get_current_user_unauthenticated(self, client):
        """Test getting current user without authentication."""
        # Attempt to get current user without authentication
        response = await client.get("/user/me")
        assert response.status_code == 401
        assert response.json() == {"detail": "Not authenticated"}

    async def test_logout_user(self, client, user_data):
        """Test logging out a user with valid token."""
        # Register
        await register(client, user_data)

        # Login to get token
        login_response = await login(client, user_data)
        access_token = login_response.json()["access_token"]

        # Logout
        response = await client.post(
            "/user/logout", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200

    async def test_multiple_users(self, client, user_data, alt_user_data):
        """Test that multiple users can be registered independently."""
        # Register first user
        response1 = await register(client, user_data)
        assert response1.status_code == 200

        # Register second user
        response2 = await register(client, alt_user_data)
        assert response2.status_code == 200

        # Login as first user
        login1 = await login(client, user_data)
        assert login1.status_code == 200

        # Login as second user
        login2 = await login(client, alt_user_data)
        assert login2.status_code == 200

    async def test_delete_user(self, client, user_data):
        """Test deleting a user."""
        # Register user first
        response = await register(client, user_data)
        assert response.status_code == 200

        # Login to get token
        login_response = await login(client, user_data)
        access_token = login_response.json()["access_token"]

        # Delete user - include the password parameter
        response = await client.delete(
            f"/user/?password={user_data['password']}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        assert "status" in response.json()

        # Try to get current user after deletion
        response = await client.get(
            "/user/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 401
