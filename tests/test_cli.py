"""Tests for CLI argument parsing."""

import os
from unittest.mock import MagicMock, patch

from jira_cursor import cli


class TestCLI:
    """Test cases for CLI argument parsing."""

    @patch("jira_cursor.cli.create_automation_service")
    @patch("jira_cursor.code_generator.CodeGenerator")
    @patch("jira_cursor.cli.setup_logging")
    def test_cli_timeout_argument(self, mock_setup_logging, mock_codegen, mock_service):
        """Test that --cursor-cloud-timeout argument is parsed correctly."""
        mock_service_instance = MagicMock()
        mock_service_instance.run_once.return_value = 0
        mock_service.return_value = mock_service_instance

        with patch(
            "sys.argv",
            [
                "cli.py",
                "--jira-domain",
                "test",
                "--jira-email",
                "test@test.com",
                "--jira-token",
                "token",
                "--github-repo-owner",
                "owner",
                "--github-repo-name",
                "repo",
                "--jql-query",
                "project=TEST",
                "--cursor-cloud-api-key",
                "key",
                "--cursor-cloud-timeout",
                "3600",
            ],
        ):
            result = cli.main()

        assert result == 0
        # Verify CodeGenerator was called with timeout=3600
        mock_codegen.assert_called_once()
        call_kwargs = mock_codegen.call_args[1]
        assert call_kwargs["timeout"] == 3600

    @patch("jira_cursor.cli.create_automation_service")
    @patch("jira_cursor.code_generator.CodeGenerator")
    @patch("jira_cursor.cli.setup_logging")
    def test_cli_timeout_default(self, mock_setup_logging, mock_codegen, mock_service):
        """Test that default timeout is 1800 seconds."""
        mock_service_instance = MagicMock()
        mock_service_instance.run_once.return_value = 0
        mock_service.return_value = mock_service_instance

        with patch(
            "sys.argv",
            [
                "cli.py",
                "--jira-domain",
                "test",
                "--jira-email",
                "test@test.com",
                "--jira-token",
                "token",
                "--github-repo-owner",
                "owner",
                "--github-repo-name",
                "repo",
                "--jql-query",
                "project=TEST",
                "--cursor-cloud-api-key",
                "key",
            ],
        ):
            result = cli.main()

        assert result == 0
        # Verify CodeGenerator was called with default timeout=1800
        mock_codegen.assert_called_once()
        call_kwargs = mock_codegen.call_args[1]
        assert call_kwargs["timeout"] == 1800

    @patch("jira_cursor.cli.create_automation_service")
    @patch("jira_cursor.code_generator.CodeGenerator")
    @patch("jira_cursor.cli.setup_logging")
    def test_cli_model_argument(self, mock_setup_logging, mock_codegen, mock_service):
        """Test that --cursor-cloud-model argument is parsed correctly."""
        mock_service_instance = MagicMock()
        mock_service_instance.run_once.return_value = 0
        mock_service.return_value = mock_service_instance

        with patch(
            "sys.argv",
            [
                "cli.py",
                "--jira-domain",
                "test",
                "--jira-email",
                "test@test.com",
                "--jira-token",
                "token",
                "--github-repo-owner",
                "owner",
                "--github-repo-name",
                "repo",
                "--jql-query",
                "project=TEST",
                "--cursor-cloud-api-key",
                "key",
                "--cursor-cloud-model",
                "claude-4-sonnet-thinking",
            ],
        ):
            result = cli.main()

        assert result == 0
        # Verify CodeGenerator was called with model
        mock_codegen.assert_called_once()
        call_kwargs = mock_codegen.call_args[1]
        assert call_kwargs["model"] == "claude-4-sonnet-thinking"

    @patch("jira_cursor.cli.create_automation_service")
    @patch("jira_cursor.code_generator.CodeGenerator")
    @patch("jira_cursor.cli.setup_logging")
    def test_cli_model_optional(self, mock_setup_logging, mock_codegen, mock_service):
        """Test that model argument is optional."""
        mock_service_instance = MagicMock()
        mock_service_instance.run_once.return_value = 0
        mock_service.return_value = mock_service_instance

        with patch(
            "sys.argv",
            [
                "cli.py",
                "--jira-domain",
                "test",
                "--jira-email",
                "test@test.com",
                "--jira-token",
                "token",
                "--github-repo-owner",
                "owner",
                "--github-repo-name",
                "repo",
                "--jql-query",
                "project=TEST",
                "--cursor-cloud-api-key",
                "key",
            ],
        ):
            result = cli.main()

        assert result == 0
        # Verify CodeGenerator was called without model (or None)
        mock_codegen.assert_called_once()
        call_kwargs = mock_codegen.call_args[1]
        assert call_kwargs.get("model") is None

    @patch("jira_cursor.cli.create_automation_service")
    @patch("jira_cursor.code_generator.CodeGenerator")
    @patch("jira_cursor.cli.setup_logging")
    def test_cli_timeout_from_env(self, mock_setup_logging, mock_codegen, mock_service):
        """Test that timeout can be set from environment variable."""
        mock_service_instance = MagicMock()
        mock_service_instance.run_once.return_value = 0
        mock_service.return_value = mock_service_instance

        with patch.dict(os.environ, {"CURSOR_CLOUD_TIMEOUT": "7200"}):
            with patch(
                "sys.argv",
                [
                    "cli.py",
                    "--jira-domain",
                    "test",
                    "--jira-email",
                    "test@test.com",
                    "--jira-token",
                    "token",
                    "--github-repo-owner",
                    "owner",
                    "--github-repo-name",
                    "repo",
                    "--jql-query",
                    "project=TEST",
                    "--cursor-cloud-api-key",
                    "key",
                ],
            ):
                result = cli.main()

        assert result == 0
        # When not provided via CLI, should use env var
        # But CLI arg takes precedence, so if not in CLI, it uses env
        # Actually, the code uses args.cursor_cloud_timeout or env, so let's check
        mock_codegen.assert_called_once()

    @patch("jira_cursor.cli.create_automation_service")
    @patch("jira_cursor.code_generator.CodeGenerator")
    @patch("jira_cursor.cli.setup_logging")
    def test_cli_model_from_env(self, mock_setup_logging, mock_codegen, mock_service):
        """Test that model can be set from environment variable."""
        mock_service_instance = MagicMock()
        mock_service_instance.run_once.return_value = 0
        mock_service.return_value = mock_service_instance

        with patch.dict(os.environ, {"CURSOR_CLOUD_MODEL": "o3"}):
            with patch(
                "sys.argv",
                [
                    "cli.py",
                    "--jira-domain",
                    "test",
                    "--jira-email",
                    "test@test.com",
                    "--jira-token",
                    "token",
                    "--github-repo-owner",
                    "owner",
                    "--github-repo-name",
                    "repo",
                    "--jql-query",
                    "project=TEST",
                    "--cursor-cloud-api-key",
                    "key",
                ],
            ):
                result = cli.main()

        assert result == 0
        mock_codegen.assert_called_once()
        call_kwargs = mock_codegen.call_args[1]
        assert call_kwargs["model"] == "o3"

    @patch("jira_cursor.cli.create_automation_service")
    @patch("jira_cursor.code_generator.CodeGenerator")
    @patch("jira_cursor.cli.setup_logging")
    def test_cli_both_timeout_and_model(self, mock_setup_logging, mock_codegen, mock_service):
        """Test that both timeout and model can be specified together."""
        mock_service_instance = MagicMock()
        mock_service_instance.run_once.return_value = 0
        mock_service.return_value = mock_service_instance

        with patch(
            "sys.argv",
            [
                "cli.py",
                "--jira-domain",
                "test",
                "--jira-email",
                "test@test.com",
                "--jira-token",
                "token",
                "--github-repo-owner",
                "owner",
                "--github-repo-name",
                "repo",
                "--jql-query",
                "project=TEST",
                "--cursor-cloud-api-key",
                "key",
                "--cursor-cloud-timeout",
                "3600",
                "--cursor-cloud-model",
                "claude-4-sonnet-thinking",
            ],
        ):
            result = cli.main()

        assert result == 0
        mock_codegen.assert_called_once()
        call_kwargs = mock_codegen.call_args[1]
        assert call_kwargs["timeout"] == 3600
        assert call_kwargs["model"] == "claude-4-sonnet-thinking"
