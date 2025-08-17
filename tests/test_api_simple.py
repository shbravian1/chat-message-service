# tests/test_api_simple.py
"""
Simplified API tests that work with existing database
"""
import pytest
import io
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings

# Test configuration
client = TestClient(app)
settings = get_settings()

# Test constants
TEST_USER_ID = "test_user_pytest"
VALID_HEADERS = {"X-API-Key": settings.api_key}
INVALID_HEADERS = {"X-API-Key": "invalid_key_123"}


class TestBasicEndpoints:
    """Test basic endpoints without database modifications"""

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Chat Storage API"
        assert data["docs"] == "/docs"

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data


class TestAuthentication:
    """Test API authentication"""

    def test_missing_api_key(self):
        """Test request without API key"""
        response = client.get(f"/api/v1/sessions?user_id={TEST_USER_ID}")
        assert response.status_code == 401

    def test_invalid_api_key(self):
        """Test request with invalid API key"""
        response = client.get(
            f"/api/v1/sessions?user_id={TEST_USER_ID}",
            headers=INVALID_HEADERS
        )
        assert response.status_code == 401

    def test_valid_api_key(self):
        """Test request with valid API key"""
        response = client.get(
            f"/api/v1/sessions?user_id={TEST_USER_ID}",
            headers=VALID_HEADERS
        )
        assert response.status_code == 200


class TestSessionOperations:
    """Test session operations with cleanup"""

    def setup_method(self):
        """Clean up before each test"""
        # Delete any existing test sessions
        sessions_response = client.get(
            f"/api/v1/sessions?user_id={TEST_USER_ID}",
            headers=VALID_HEADERS
        )
        if sessions_response.status_code == 200:
            sessions = sessions_response.json()
            for session in sessions:
                client.delete(
                    f"/api/v1/sessions/{session['id']}",
                    headers=VALID_HEADERS
                )

    def teardown_method(self):
        """Clean up after each test"""
        self.setup_method()

    def test_create_and_list_sessions(self):
        """Test creating and listing sessions"""
        # Create a session
        create_response = client.post(
            "/api/v1/sessions",
            headers=VALID_HEADERS,
            json={"user_id": TEST_USER_ID, "title": "Test Session"}
        )
        assert create_response.status_code == 200
        session_data = create_response.json()
        assert session_data["title"] == "Test Session"
        assert session_data["user_id"] == TEST_USER_ID
        session_id = session_data["id"]

        # List sessions
        list_response = client.get(
            f"/api/v1/sessions?user_id={TEST_USER_ID}",
            headers=VALID_HEADERS
        )
        assert list_response.status_code == 200
        sessions = list_response.json()
        assert len(sessions) >= 1
        assert any(s["id"] == session_id for s in sessions)

    def test_get_session(self):
        """Test getting a specific session"""
        # Create a session
        create_response = client.post(
            "/api/v1/sessions",
            headers=VALID_HEADERS,
            json={"user_id": TEST_USER_ID, "title": "Get Test Session"}
        )
        session_id = create_response.json()["id"]

        # Get the session
        get_response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=VALID_HEADERS
        )
        assert get_response.status_code == 200
        session_data = get_response.json()
        assert session_data["title"] == "Get Test Session"
        assert session_data["id"] == session_id

    def test_update_session(self):
        """Test updating a session"""
        # Create a session
        create_response = client.post(
            "/api/v1/sessions",
            headers=VALID_HEADERS,
            json={"user_id": TEST_USER_ID, "title": "Original Title"}
        )
        session_id = create_response.json()["id"]

        # Update the session
        update_response = client.put(
            f"/api/v1/sessions/{session_id}",
            headers=VALID_HEADERS,
            json={"title": "Updated Title"}
        )
        assert update_response.status_code == 200
        updated_session = update_response.json()
        assert updated_session["title"] == "Updated Title"

    def test_toggle_favorite(self):
        """Test toggling session favorite status"""
        # Create a session
        create_response = client.post(
            "/api/v1/sessions",
            headers=VALID_HEADERS,
            json={"user_id": TEST_USER_ID, "title": "Favorite Test"}
        )
        session_id = create_response.json()["id"]

        # Toggle favorite (should become True)
        toggle_response = client.patch(
            f"/api/v1/sessions/{session_id}/favorite",
            headers=VALID_HEADERS
        )
        assert toggle_response.status_code == 200
        assert toggle_response.json()["is_favorite"] is True

        # Toggle again (should become False)
        toggle_response2 = client.patch(
            f"/api/v1/sessions/{session_id}/favorite",
            headers=VALID_HEADERS
        )
        assert toggle_response2.status_code == 200
        assert toggle_response2.json()["is_favorite"] is False

    def test_delete_session(self):
        """Test deleting a session"""
        # Create a session
        create_response = client.post(
            "/api/v1/sessions",
            headers=VALID_HEADERS,
            json={"user_id": TEST_USER_ID, "title": "Delete Test"}
        )
        session_id = create_response.json()["id"]

        # Delete the session
        delete_response = client.delete(
            f"/api/v1/sessions/{session_id}",
            headers=VALID_HEADERS
        )
        assert delete_response.status_code == 200

        # Verify deletion
        get_response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=VALID_HEADERS
        )
        assert get_response.status_code == 404


class TestMessageOperations:
    """Test message operations"""

    @pytest.fixture
    def test_session(self):
        """Create a test session"""
        response = client.post(
            "/api/v1/sessions",
            headers=VALID_HEADERS,
            json={"user_id": TEST_USER_ID, "title": "Message Test Session"}
        )
        session_id = response.json()["id"]
        yield session_id
        # Cleanup
        client.delete(f"/api/v1/sessions/{session_id}", headers=VALID_HEADERS)

    def test_add_message(self, test_session):
        """Test adding a message to a session"""
        response = client.post(
            f"/api/v1/sessions/{test_session}/messages",
            headers=VALID_HEADERS,
            json={
                "sender": "user",
                "content": "Test message content",
                "context_metadata": {"type": "test"}
            }
        )
        assert response.status_code == 200
        message_data = response.json()
        assert message_data["sender"] == "user"
        assert message_data["content"] == "Test message content"
        assert message_data["context_metadata"]["type"] == "test"

    def test_get_messages(self, test_session):
        """Test getting messages from a session"""
        # Add a message first
        client.post(
            f"/api/v1/sessions/{test_session}/messages",
            headers=VALID_HEADERS,
            json={
                "sender": "user",
                "content": "Test message for retrieval"
            }
        )

        # Get messages
        response = client.get(
            f"/api/v1/sessions/{test_session}/messages",
            headers=VALID_HEADERS
        )
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert "total" in data
        assert data["total"] >= 1


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])