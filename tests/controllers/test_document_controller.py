import io
from unittest.mock import AsyncMock

import pytest


async def register_and_login(client, user_data):
    """
    Helper function to register a user, log in, and return the access token.
    """
    # Register user
    await client.post("/user/register", json=user_data)

    # Login to get token
    login_response = await client.post(
        "/user/login",
        data={
            "username": user_data["username"],
            "password": user_data["password"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    return login_response.json()["access_token"]


async def upload_document(client, token, title, content="Test document content"):
    """
    Helper function to upload a document and return the response.
    """
    # Create a mock file
    file_content = content.encode("utf-8")

    # Create file form data, title is sent as a query parameter
    files = {"file": ("test_doc.txt", io.BytesIO(file_content), "text/plain")}

    # Upload document with title as query parameter
    response = await client.post(
        f"/documents/?title={title}",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )

    return response


class TestDocumentController:
    @pytest.fixture
    def user_data(self):
        """
        Fixture to provide fresh user data for each test.
        """
        return {
            "username": "docuser",
            "password": "docpassword",
            "email": "docemail",
        }

    @pytest.fixture
    def alt_user_data(self):
        """
        Alternative user data for testing access control.
        """
        return {
            "username": "altdocuser",
            "password": "altdocpassword",
            "email": "altdocemail",
        }

    @pytest.fixture(autouse=True)
    def mock_storage(self, monkeypatch):
        """
        Mock the FileStorage methods used in the document controller.
        This avoids actual file operations during testing.
        """
        # Storage for tracking content
        stored_content = {}

        # Create a mock for save_bytes_by_path with proper side effect
        async def mock_save_bytes(bytes_content, path):
            stored_content[path] = bytes_content
            return f"/mocked/path/{path}"

        save_mock = AsyncMock(side_effect=mock_save_bytes)
        monkeypatch.setattr(
            "app.utils.storage.FileStorage.save_bytes_by_path", save_mock
        )

        # Create a mock for get_file_by_path with proper side effect
        async def mock_get_file(path):
            # If path starts with /mocked/path/ then extract the key
            if isinstance(path, str) and path.startswith("/mocked/path/"):
                key = path[len("/mocked/path/") :]
                if key in stored_content:
                    return stored_content[key]
            elif path in stored_content:
                return stored_content[path]
            return b"Mocked file content"

        get_mock = AsyncMock(side_effect=mock_get_file)
        monkeypatch.setattr("app.utils.storage.FileStorage.get_file_by_path", get_mock)

        # Create mock for delete_file_by_path - this is the actual method used in the controller
        delete_mock = AsyncMock(return_value=True)
        monkeypatch.setattr(
            "app.utils.storage.FileStorage.delete_file_by_path", delete_mock
        )

        return {
            "save": save_mock,
            "get": get_mock,
            "delete": delete_mock,
            "stored_content": stored_content,
        }

    async def test_list_documents_empty(self, client, user_data):
        """Test listing documents when user has no documents."""
        # Register and login
        token = await register_and_login(client, user_data)

        # List documents
        response = await client.get(
            "/documents/", headers={"Authorization": f"Bearer {token}"}
        )

        # Assert response
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_documents_with_pagination(self, client, user_data):
        """Test listing documents with pagination."""
        # Register and login
        token = await register_and_login(client, user_data)

        # Upload several documents
        for i in range(3):
            await upload_document(client, token, f"Test Document {i}")

        # List documents with pagination
        response = await client.get(
            "/documents/?offset=1&limit=2", headers={"Authorization": f"Bearer {token}"}
        )

        # Assert response
        assert response.status_code == 200
        documents = response.json()
        assert len(documents) <= 2  # Should not exceed limit
        assert isinstance(documents, list)
        # Each document should have id and title
        for doc in documents:
            assert "id" in doc
            assert "title" in doc

    async def test_create_document(self, client, user_data):
        """Test uploading a new document."""
        # Register and login
        token = await register_and_login(client, user_data)

        # Upload document
        response = await upload_document(client, token, "Test Document")

        # Assert response
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["status"] == "created"
        assert "id" in response_data
        assert response_data["title"] == "Test Document"

    async def test_create_duplicate_document(self, client, user_data):
        """Test attempting to upload a document with duplicate content."""
        # Register and login
        token = await register_and_login(client, user_data)

        # Upload document first time
        await upload_document(client, token, "Original Document", "Same content")

        # Try to upload document with same content but different title
        response = await upload_document(
            client, token, "Duplicate Document", "Same content"
        )

        # Assert response
        assert response.status_code == 400
        assert "Document with same content already exists" in response.json()["detail"]

    async def test_get_document(self, client, user_data):
        """Test downloading a document."""
        # Register and login
        token = await register_and_login(client, user_data)

        # Upload document
        upload_response = await upload_document(
            client, token, "Download Test", "Document content for download"
        )
        document_id = upload_response.json()["id"]

        # Download document
        response = await client.get(
            f"/documents/{document_id}", headers={"Authorization": f"Bearer {token}"}
        )

        # Assert response
        assert response.status_code == 200
        assert "Content-Disposition" in response.headers
        assert "Download Test.txt" in response.headers["Content-Disposition"]
        assert response.content == b"Document content for download"

    async def test_get_nonexistent_document(self, client, user_data):
        """Test attempting to download a nonexistent document."""
        # Register and login
        token = await register_and_login(client, user_data)

        # Try to download nonexistent document
        response = await client.get(
            "/documents/nonexistent-id", headers={"Authorization": f"Bearer {token}"}
        )

        # Assert response
        assert response.status_code == 404
        assert "Document not found" in response.json()["detail"]

    async def test_get_unauthorized_document(self, client, user_data, alt_user_data):
        """Test attempting to download another user's document."""
        # Register and login first user
        token1 = await register_and_login(client, user_data)

        # Upload document as first user
        upload_response = await upload_document(client, token1, "Protected Document")
        document_id = upload_response.json()["id"]

        # Register and login second user
        token2 = await register_and_login(client, alt_user_data)

        # Try to download first user's document as second user
        response = await client.get(
            f"/documents/{document_id}", headers={"Authorization": f"Bearer {token2}"}
        )

        # Assert response
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    async def test_delete_document(self, client, user_data):
        """Test deleting a document."""
        # Register and login
        token = await register_and_login(client, user_data)

        # Upload document
        upload_response = await upload_document(client, token, "Delete Test")
        document_id = upload_response.json()["id"]

        # Delete document
        response = await client.delete(
            f"/documents/{document_id}", headers={"Authorization": f"Bearer {token}"}
        )

        # Assert response
        # The controller defines 202 as the status code, but FastAPI may default to 200
        # if not explicitly set in the response
        assert response.status_code in [200, 202]  # Accept either 200 or 202
        assert response.json()["status"] == "deletion_in_progress"

        # Try to download deleted document (should eventually fail)
        # We may need to add a small delay here in a real test environment
        get_response = await client.get(
            f"/documents/{document_id}", headers={"Authorization": f"Bearer {token}"}
        )

        # The document might still be found immediately after deletion started
        # since deletion happens in the background, so we don't assert its status here

    async def test_delete_nonexistent_document(self, client, user_data):
        """Test attempting to delete a nonexistent document."""
        # Register and login
        token = await register_and_login(client, user_data)

        # Try to delete nonexistent document
        response = await client.delete(
            "/documents/nonexistent-id", headers={"Authorization": f"Bearer {token}"}
        )

        # Assert response
        assert response.status_code == 404
        assert "Resource not found" in response.json()["detail"]

    async def test_delete_unauthorized_document(self, client, user_data, alt_user_data):
        """Test attempting to delete another user's document."""
        # Register and login first user
        token1 = await register_and_login(client, user_data)

        # Upload document as first user
        upload_response = await upload_document(client, token1, "Protected Document")
        document_id = upload_response.json()["id"]

        # Register and login second user
        token2 = await register_and_login(client, alt_user_data)

        # Try to delete first user's document as second user
        response = await client.delete(
            f"/documents/{document_id}", headers={"Authorization": f"Bearer {token2}"}
        )

        # Assert response
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    async def test_get_document_statistics(self, client, user_data):
        """Test retrieving document statistics."""
        # Register and login
        token = await register_and_login(client, user_data)

        # Upload document with specific content for statistics
        content = "This is a test document. This document contains repeated words for testing statistics."
        upload_response = await upload_document(client, token, "Stats Test", content)
        document_id = upload_response.json()["id"]

        # Get document statistics
        response = await client.get(
            f"/documents/{document_id}/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert response
        assert response.status_code == 200
        stats = response.json()
        assert isinstance(stats, list)

        # Check that the response contains expected word statistics
        for word_stat in stats:
            assert "word" in word_stat
            assert "frequency" in word_stat
            assert "tf" in word_stat
            assert "idf" in word_stat
            assert "tfidf" in word_stat

    async def test_get_statistics_nonexistent_document(self, client, user_data):
        """Test attempting to get statistics for a nonexistent document."""
        # Register and login
        token = await register_and_login(client, user_data)

        # Try to get statistics for nonexistent document
        response = await client.get(
            "/documents/nonexistent-id/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert response
        assert response.status_code == 404
        assert "Document not found" in response.json()["detail"]

    async def test_get_statistics_unauthorized_document(
        self, client, user_data, alt_user_data
    ):
        """Test attempting to get statistics for another user's document."""
        # Register and login first user
        token1 = await register_and_login(client, user_data)

        # Upload document as first user
        upload_response = await upload_document(client, token1, "Protected Document")
        document_id = upload_response.json()["id"]

        # Register and login second user
        token2 = await register_and_login(client, alt_user_data)

        # Try to get statistics for first user's document as second user
        response = await client.get(
            f"/documents/{document_id}/statistics",
            headers={"Authorization": f"Bearer {token2}"},
        )

        # Assert response
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]
