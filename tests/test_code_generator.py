"""Tests for CodeGenerator."""

from unittest.mock import MagicMock, patch

from jira_cursor.code_generator import CodeGenerator


class TestCodeGenerator:
    """Test cases for CodeGenerator."""

    def test_init_with_timeout_and_model(self):
        """Test that CodeGenerator initializes with timeout and model."""
        generator = CodeGenerator(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
            timeout=3600,
            model="claude-4-sonnet-thinking",
        )
        assert generator.cursor_client.timeout == 3600
        assert generator.cursor_client.model == "claude-4-sonnet-thinking"

    def test_init_default_timeout(self):
        """Test that default timeout is 1800 seconds."""
        generator = CodeGenerator(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
        )
        assert generator.cursor_client.timeout == 1800

    @patch("jira_cursor.code_generator.CursorCloudClient.generate_code")
    def test_generate_code_changes_calls_client(self, mock_generate_code):
        """Test that generate_code_changes calls cursor_client.generate_code."""
        mock_generate_code.return_value = {"status": "finished", "pr_url": "test_url"}

        generator = CodeGenerator(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
        )

        ticket = {"key": "TEST-123"}
        requirements = {
            "summary": "Test ticket",
            "description": "Test description",
            "file_references": [],
        }

        result = generator.generate_code_changes(ticket, requirements)

        assert result is not None
        assert result["status"] == "finished"
        mock_generate_code.assert_called_once()

    @patch("jira_cursor.code_generator.CursorCloudClient.generate_code")
    def test_generate_code_changes_with_timeout(self, mock_generate_code):
        """Test that timeout is passed through to cursor client."""
        mock_generate_code.return_value = {"status": "finished"}

        generator = CodeGenerator(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
            timeout=3600,
        )

        ticket = {"key": "TEST-123"}
        requirements = {
            "summary": "Test ticket",
            "description": "Test description",
            "file_references": [],
        }

        generator.generate_code_changes(ticket, requirements)

        # Verify timeout is set on client
        assert generator.cursor_client.timeout == 3600

    @patch("jira_cursor.code_generator.CursorCloudClient.generate_code")
    def test_generate_code_changes_with_model(self, mock_generate_code):
        """Test that model is passed through to cursor client."""
        mock_generate_code.return_value = {"status": "finished"}

        generator = CodeGenerator(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
            model="claude-4-sonnet-thinking",
        )

        ticket = {"key": "TEST-123"}
        requirements = {
            "summary": "Test ticket",
            "description": "Test description",
            "file_references": [],
        }

        generator.generate_code_changes(ticket, requirements)

        # Verify model is set on client
        assert generator.cursor_client.model == "claude-4-sonnet-thinking"

    def test_build_generation_prompt(self):
        """Test that _build_generation_prompt creates correct prompt."""
        generator = CodeGenerator(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
        )

        prompt = generator._build_generation_prompt(
            ticket_key="TEST-123",
            summary="Test Summary",
            description="Test Description",
            labels=["bug", "urgent"],
        )

        assert "TEST-123" in prompt
        assert "Test Summary" in prompt
        assert "Test Description" in prompt
        assert "bug" in prompt
        assert "urgent" in prompt
        
        # Verify commit message and PR naming requirements are present
        assert "IMPORTANT - Commit Messages and PR Naming Requirements" in prompt
        assert "ALL commit messages MUST start with the ticket ID" in prompt
        assert "PR title/name MUST include the ticket ID" in prompt
        assert "TEST-123: Add new feature" in prompt or "TEST-123:" in prompt
        assert "REQUIRED for all commits and the PR" in prompt

    def test_create_branch_name(self):
        """Test that _create_branch_name creates valid branch name."""
        generator = CodeGenerator(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
        )

        branch_name = generator._create_branch_name("TEST-123", "Fix bug in code")

        assert branch_name.startswith("test-123/")
        assert "fix" in branch_name.lower()
        assert "bug" in branch_name.lower()

    def test_create_branch_name_feature_prefix(self):
        """Test that feature prefix is used for non-bug tickets."""
        generator = CodeGenerator(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
        )

        branch_name = generator._create_branch_name("TEST-123", "Add new feature")

        assert branch_name.startswith("test-123/")
        assert "feature" in branch_name.lower()

    @patch("jira_cursor.code_generator.JiraClient")
    def test_read_file_contents_from_jira(self, mock_jira_client_class):
        """Test reading file contents from Jira attachments."""
        mock_jira_client = MagicMock()
        mock_jira_client_class.return_value = mock_jira_client
        mock_jira_client.get_ticket_attachments.return_value = [
            {
                "id": "att_123",
                "filename": "test.py",
                "content": "https://jira.example.com/attachment/test.py",
            }
        ]
        mock_jira_client.download_attachment.return_value = "file content here"

        generator = CodeGenerator(
            api_key="test_key",
            jira_client=mock_jira_client,
            repository_url="https://github.com/test/repo",
        )

        file_contents = generator._read_file_contents_from_jira("TEST-123", ["test.py"])

        assert file_contents is not None
        assert "test.py" in file_contents
        assert file_contents["test.py"] == "file content here"

    def test_analyze_codebase_context(self):
        """Test that analyze_codebase_context creates context string."""
        generator = CodeGenerator(
            api_key="test_key",
            repository_url="https://github.com/test/repo",
        )

        context = generator.analyze_codebase_context(
            file_references=["src/file1.py", "src/file2.py"],
            ticket_requirements={"description": "Test description"},
        )

        assert "file1.py" in context
        assert "file2.py" in context
        assert "Test description" in context
