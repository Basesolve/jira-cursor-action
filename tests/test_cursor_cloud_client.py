"""Tests for CursorCloudClient."""

from unittest.mock import MagicMock, patch

from jira_cursor.cursor_cloud_client import CursorCloudClient


class TestCursorCloudClient:
    """Test cases for CursorCloudClient."""

    def test_init_with_timeout_and_model(self):
        """Test that CursorCloudClient initializes with timeout and model."""
        client = CursorCloudClient(
            api_key="test_key",
            base_url="https://api.cursor.com",
            repository_url="https://github.com/test/repo",
            timeout=3600,
            model="claude-4-sonnet-thinking",
        )
        assert client.timeout == 3600
        assert client.model == "claude-4-sonnet-thinking"

    def test_init_default_timeout(self):
        """Test that default timeout is 1800 seconds."""
        client = CursorCloudClient(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
        )
        assert client.timeout == 1800

    @patch("jira_cursor.cursor_cloud_client.requests.get")
    def test_get_supported_models_success(self, mock_get):
        """Test get_supported_models with successful API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": ["claude-4-sonnet-thinking", "o3", "claude-4-opus-thinking"]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = CursorCloudClient(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
        )
        models = client.get_supported_models()

        assert models == ["claude-4-sonnet-thinking", "o3", "claude-4-opus-thinking"]
        mock_get.assert_called_once()

    @patch("jira_cursor.cursor_cloud_client.requests.get")
    def test_get_supported_models_failure(self, mock_get):
        """Test get_supported_models with API failure."""
        mock_get.side_effect = Exception("API Error")

        client = CursorCloudClient(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
        )
        models = client.get_supported_models()

        assert models is None

    @patch("jira_cursor.cursor_cloud_client.requests.get")
    def test_get_supported_models_invalid_response(self, mock_get):
        """Test get_supported_models with invalid response format."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"invalid": "data"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = CursorCloudClient(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
        )
        models = client.get_supported_models()

        assert models is None

    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient.get_supported_models")
    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient._call_api_with_retry")
    def test_build_agent_creation_payload_with_valid_model(self, mock_api_call, mock_get_models):
        """Test that valid model is included in payload."""
        mock_get_models.return_value = ["claude-4-sonnet-thinking", "o3"]
        mock_api_call.return_value = {"id": "test_agent"}

        client = CursorCloudClient(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
            model="claude-4-sonnet-thinking",
        )

        payload = client._build_agent_creation_payload(
            prompt="test prompt",
            context=None,
            file_references=None,
            codebase_context=None,
            branch_name="test-branch",
            auto_create_pr=True,
        )

        assert payload["model"] == "claude-4-sonnet-thinking"
        mock_get_models.assert_called_once()

    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient.get_supported_models")
    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient._call_api_with_retry")
    def test_build_agent_creation_payload_with_invalid_model(self, mock_api_call, mock_get_models):
        """Test that invalid model is ignored."""
        mock_get_models.return_value = ["claude-4-sonnet-thinking", "o3"]
        mock_api_call.return_value = {"id": "test_agent"}

        client = CursorCloudClient(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
            model="invalid-model",
        )

        payload = client._build_agent_creation_payload(
            prompt="test prompt",
            context=None,
            file_references=None,
            codebase_context=None,
            branch_name="test-branch",
            auto_create_pr=True,
        )

        assert "model" not in payload
        mock_get_models.assert_called_once()

    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient.get_supported_models")
    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient._call_api_with_retry")
    def test_build_agent_creation_payload_model_api_failure(self, mock_api_call, mock_get_models):
        """Test that model is ignored when models API fails."""
        mock_get_models.return_value = None
        mock_api_call.return_value = {"id": "test_agent"}

        client = CursorCloudClient(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
            model="claude-4-sonnet-thinking",
        )

        payload = client._build_agent_creation_payload(
            prompt="test prompt",
            context=None,
            file_references=None,
            codebase_context=None,
            branch_name="test-branch",
            auto_create_pr=True,
        )

        assert "model" not in payload
        mock_get_models.assert_called_once()

    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient.get_supported_models")
    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient._call_api_with_retry")
    def test_build_agent_creation_payload_without_model(self, mock_api_call, mock_get_models):
        """Test that model is not included when not provided."""
        mock_api_call.return_value = {"id": "test_agent"}

        client = CursorCloudClient(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
        )

        payload = client._build_agent_creation_payload(
            prompt="test prompt",
            context=None,
            file_references=None,
            codebase_context=None,
            branch_name="test-branch",
            auto_create_pr=True,
        )

        assert "model" not in payload
        mock_get_models.assert_not_called()

    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient.get_supported_models")
    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient._call_api_with_retry")
    def test_build_agent_creation_payload_open_as_cursor_app(self, mock_api_call, mock_get_models):
        """Test that openAsCursorGithubApp is set to True in target."""
        mock_api_call.return_value = {"id": "test_agent"}

        client = CursorCloudClient(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
        )

        payload = client._build_agent_creation_payload(
            prompt="test prompt",
            context=None,
            file_references=None,
            codebase_context=None,
            branch_name="test-branch",
            auto_create_pr=True,
        )

        assert payload["target"]["openAsCursorGithubApp"] is True

    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient.get_supported_models")
    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient._call_api_with_retry")
    def test_build_agent_creation_payload_target_section(self, mock_api_call, mock_get_models):
        """Test that target section includes all required fields."""
        mock_api_call.return_value = {"id": "test_agent"}

        client = CursorCloudClient(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
        )

        payload = client._build_agent_creation_payload(
            prompt="test prompt",
            context=None,
            file_references=None,
            codebase_context=None,
            branch_name="test-branch",
            auto_create_pr=True,
        )

        assert "target" in payload
        assert payload["target"]["branchName"] == "test-branch"
        assert payload["target"]["autoCreatePr"] is True
        assert payload["target"]["openAsCursorGithubApp"] is True

    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient.get_agent_status")
    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient.create_agent")
    def test_wait_for_agent_completion_timeout(self, mock_create_agent, mock_get_status):
        """Test that _wait_for_agent_completion respects timeout."""

        mock_create_agent.return_value = "test_agent_id"
        # Mock status to always return RUNNING to trigger timeout
        mock_get_status.return_value = {"status": "RUNNING"}

        client = CursorCloudClient(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
            timeout=2,  # Very short timeout for testing
        )

        result = client._wait_for_agent_completion(
            agent_id="test_agent_id",
            max_wait_time=2,
            poll_interval=1,
        )

        # Should timeout and return None
        assert result is None

    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient.get_agent_status")
    def test_wait_for_agent_completion_finished(self, mock_get_status):
        """Test that _wait_for_agent_completion handles FINISHED status."""
        mock_get_status.return_value = {
            "status": "FINISHED",
            "target": {"prUrl": "https://github.com/test/repo/pull/123"},
        }

        client = CursorCloudClient(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
        )

        result = client._wait_for_agent_completion(
            agent_id="test_agent_id",
            max_wait_time=600,
            poll_interval=1,
        )

        assert result is not None
        assert result["status"] == "finished"
        assert result["pr_url"] == "https://github.com/test/repo/pull/123"

    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient.get_agent_status")
    def test_wait_for_agent_completion_error(self, mock_get_status):
        """Test that _wait_for_agent_completion handles ERROR status."""
        mock_get_status.return_value = {"status": "ERROR", "error": "Test error"}

        client = CursorCloudClient(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
        )

        result = client._wait_for_agent_completion(
            agent_id="test_agent_id",
            max_wait_time=600,
            poll_interval=1,
        )

        assert result is None

    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient._wait_for_agent_completion")
    @patch("jira_cursor.cursor_cloud_client.CursorCloudClient.create_agent")
    def test_generate_code_uses_timeout(self, mock_create_agent, mock_wait_completion):
        """Test that generate_code passes timeout to _wait_for_agent_completion."""
        mock_create_agent.return_value = "test_agent_id"
        mock_wait_completion.return_value = {"status": "finished"}

        client = CursorCloudClient(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
            timeout=3600,
        )

        client.generate_code(
            prompt="test prompt",
            branch_name="test-branch",
            auto_create_pr=True,
        )

        # Verify that timeout was passed to _wait_for_agent_completion
        mock_wait_completion.assert_called_once()
        call_args = mock_wait_completion.call_args
        assert call_args.kwargs["max_wait_time"] == 3600

    @patch("jira_cursor.cursor_cloud_client.requests.post")
    def test_create_agent_api_call(self, mock_post):
        """Test that create_agent makes correct API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "test_agent_id"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        client = CursorCloudClient(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
        )

        agent_id = client.create_agent(
            prompt="test prompt",
            branch_name="test-branch",
            auto_create_pr=True,
        )

        assert agent_id == "test_agent_id"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "v0/agents" in call_args[0][0]
        payload = call_args[1]["json"]
        assert payload["target"]["openAsCursorGithubApp"] is True
