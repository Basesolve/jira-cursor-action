"""Module for generating code changes using Cursor Cloud Agents."""

import logging
from pathlib import Path
from typing import Any, Optional

from .cursor_cloud_client import CursorCloudClient
from .jira_client import JiraClient

# Configure logger
logger = logging.getLogger(__name__)

# Using lazy formatting for logging (PYL-W1201, PYL-W1202, PYL-W1203)


class CodeGenerator:
    """Generates code changes based on Jira ticket requirements.

    Uses Cursor Cloud Agents.
    """

    def __init__(
        self,
        api_key: str,
        jira_client: Optional[JiraClient] = None,
        base_url: Optional[str] = None,
        codebase_path: Optional[str] = None,
        repository_url: Optional[str] = None,
        repository_ref: Optional[str] = None,
    ):
        """Initialize code generator with Cursor Cloud Agents.

        :param api_key: Cursor Cloud API key
        :type api_key: str
        :param jira_client: Jira client for fetching attachments
            (required for Jira-hosted files)
        :type jira_client: Optional[JiraClient]
        :param base_url: Base URL for Cursor Cloud API
            (default: https://api.cursor.com)
        :type base_url: Optional[str]
        :param codebase_path: Path to codebase root for local file resolution
            (default: current working directory)
        :type codebase_path: Optional[str]
        :param repository_url: Repository URL for source (required for agent)
        :type repository_url: Optional[str]
        :param repository_ref: Repository ref/branch (default: main)
        :type repository_ref: Optional[str]
        """
        self.cursor_client = CursorCloudClient(
            api_key=api_key,
            base_url=base_url or "https://api.cursor.com",
            repository_url=repository_url,
            repository_ref=repository_ref,
        )
        self.jira_client = jira_client
        self.codebase_path = Path(codebase_path) if codebase_path else Path.cwd()
        logger.info(
            f"Initialized CodeGenerator with Cursor Cloud Agents "
            f"(jira_client: {jira_client is not None}, "
            f"codebase_path: {self.codebase_path})"
        )

    def generate_code_changes(
        self,
        ticket: dict[str, Any],
        ticket_requirements: dict[str, Any],
        codebase_context: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Generate code changes based on ticket requirements.

        Uses Cursor Cloud Agents.

        :param ticket: Jira ticket dictionary
        :type ticket: dict[str, Any]
        :param ticket_requirements: Extracted requirements from ticket
        :type ticket_requirements: dict[str, Any]
        :param codebase_context: Optional codebase context/summary
        :type codebase_context: Optional[str]
        :return: Result dictionary with generation status or None if generation failed
        :rtype: Optional[dict[str, Any]]
        """
        ticket_key = ticket.get("key", "UNKNOWN")
        summary = ticket_requirements.get("summary", "")
        description = ticket_requirements.get("description", "")
        file_references = ticket_requirements.get("file_references", [])

        logger.info(f"Generating code changes for ticket {ticket_key} using Cursor Cloud Agents")

        # Build prompt from ticket requirements
        prompt = self._build_generation_prompt(
            ticket_key=ticket_key,
            summary=summary,
            description=description,
            labels=ticket_requirements.get("labels", []),
        )

        # Separate files into Jira attachments (with contents) and repo files (names only)
        # Jira attachments need full contents since they're not in the repo
        # Repo files only need names since the agent has repo access
        jira_file_contents = self._read_file_contents_from_jira(ticket_key, file_references) or {}

        # Identify which files are in the repo (not Jira attachments)
        # These will be sent as file references only, without contents
        repo_file_references = [
            file_ref for file_ref in file_references if file_ref not in jira_file_contents
        ]

        # Only include Jira attachment contents in file_contents
        # Repo files are passed as file_references only (agent has repo access)
        file_contents = jira_file_contents

        # Create branch name for target (same logic as PRCreator)
        branch_name = self._create_branch_name(ticket_key, summary)

        # Generate code using Cursor Cloud Agents
        # Pass repo files as file_references only, Jira attachments as file_contents
        result = self.cursor_client.generate_code(
            prompt=prompt,
            context=codebase_context,
            file_references=repo_file_references,
            codebase_context=codebase_context,
            file_contents=file_contents,
            branch_name=branch_name,
            auto_create_pr=True,
        )

        if result:
            # Agent completed successfully - PR was created by Cursor
            status = result.get("status", "completed")
            logger.info(
                f"Cursor Cloud Agents completed for ticket {ticket_key} "
                f"(status: {status}). PR was created by Cursor."
            )
            return result

        logger.warning(f"Failed to generate code changes for ticket {ticket_key}")
        return None

    def _build_generation_prompt(
        self,
        ticket_key: str,
        summary: str,
        description: str,
        labels: list[str],
    ) -> str:
        """Build code generation prompt from ticket information.

        :param ticket_key: Jira ticket key
        :type ticket_key: str
        :param summary: Ticket summary
        :type summary: str
        :param description: Ticket description
        :type description: str
        :param labels: Ticket labels
        :type labels: list[str]
        :return: Generation prompt
        :rtype: str
        """
        prompt_parts = [
            f"Jira Ticket: {ticket_key}",
            f"Summary: {summary}",
            "",
            "Requirements:",
            description,
        ]

        if labels:
            prompt_parts.append(f"\nLabels: {', '.join(labels)}")

        prompt_parts.append(
            "\n\nPlease generate the code changes needed to implement this "
            "ticket. Follow the project's coding standards and security best "
            "practices."
        )

        return "\n".join(prompt_parts)

    def analyze_codebase_context(
        self,
        file_references: list[str],
        ticket_requirements: dict[str, Any],
    ) -> str:
        """Analyze codebase context for code generation.

        :param file_references: list of file paths mentioned in ticket
        :type file_references: list[str]
        :param ticket_requirements: Ticket requirements
        :type ticket_requirements: dict[str, Any]
        :return: Codebase context summary
        :rtype: str
        """
        context_parts = []

        if file_references:
            context_parts.append(f"Files mentioned in ticket: {', '.join(file_references)}")

        if ticket_requirements.get("description"):
            context_parts.append(f"Description: {ticket_requirements['description'][:500]}")

        return "\n".join(context_parts)

    def _read_file_contents_from_jira(  # noqa: C901
        self, ticket_key: str, file_references: list[str]
    ) -> Optional[dict[str, str]]:
        """Read file contents from Jira attachments.

        :param ticket_key: Jira ticket key
        :type ticket_key: str
        :param file_references: list of file paths mentioned in ticket
        :type file_references: list[str]
        :return: dictionary mapping file paths to their contents, or None if
            no Jira client
        :rtype: Optional[dict[str, str]]
        """
        if not self.jira_client:
            logger.debug("No Jira client configured, skipping Jira attachment lookup")
            return None

        file_contents: dict[str, str] = {}

        try:
            # Get attachments from Jira ticket
            attachments = self.jira_client.get_ticket_attachments(ticket_key)

            if not attachments:
                logger.debug("No attachments found for ticket %s", ticket_key)
                return None

            # Match file references to attachments
            for file_ref in file_references:
                # Extract filename from file reference
                filename = Path(file_ref).name

                # Find matching attachment
                matching_attachment = None
                for attachment in attachments:
                    attachment_filename = attachment.get("filename", "")
                    # Match by exact filename or partial match
                    if (
                        attachment_filename == filename
                        or attachment_filename.endswith(filename)
                        or filename in attachment_filename
                    ):
                        matching_attachment = attachment
                        break

                if matching_attachment:
                    # Download attachment content
                    attachment_id = matching_attachment.get("id")
                    attachment_url = matching_attachment.get("content", "")

                    if attachment_id and attachment_url:
                        content = self.jira_client.download_attachment(
                            attachment_id, attachment_url
                        )
                        if content:
                            file_contents[file_ref] = content
                            logger.info(
                                f"Downloaded file {file_ref} from Jira "
                                f"attachment {attachment_filename} "
                                f"({len(content)} chars)"
                            )
                else:
                    logger.debug(f"No matching attachment found for file reference: {file_ref}")

            if file_contents:
                logger.info(
                    f"Read {len(file_contents)} file(s) from Jira attachments "
                    f"for ticket {ticket_key}"
                )
                return file_contents

            return None

        except (OSError, ValueError, KeyError) as exc:
            # Catch specific exceptions for file operations and data access
            logger.warning(
                "Error reading files from Jira attachments for ticket %s: %s",
                ticket_key,
                exc,
            )
            return None

    def _read_file_contents_from_filesystem(self, file_references: list[str]) -> dict[str, str]:
        """Read file contents from local filesystem (fallback).

        :param file_references: list of file paths to read
        :type file_references: list[str]
        :return: dictionary mapping file paths to their contents
        :rtype: dict[str, str]
        """
        file_contents: dict[str, str] = {}

        for file_ref in file_references:
            try:
                # Resolve file path relative to codebase root
                file_path = self._resolve_file_path(file_ref)

                if file_path and file_path.exists() and file_path.is_file():
                    # Read file contents
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                        file_contents[file_ref] = content
                        logger.debug(
                            "Read file from filesystem: %s (%d chars)",
                            file_ref,
                            len(content),
                        )
                else:
                    logger.debug("File not found in filesystem: %s", file_ref)

            except (OSError, ValueError) as exc:
                # Catch specific exceptions for file operations
                logger.debug(
                    "Error reading file from filesystem %s: %s",
                    file_ref,
                    exc,
                )

        if file_contents:
            logger.info(
                "Read %d file(s) from filesystem for code generation",
                len(file_contents),
            )
        return file_contents

    def _resolve_file_path(self, file_ref: str) -> Optional[Path]:
        """Resolve file path relative to codebase root.

        :param file_ref: File reference from ticket
            (may be relative or absolute)
        :type file_ref: str
        :return: Resolved file path or None if invalid
        :rtype: Optional[Path]
        """
        # Try as-is first
        file_path = Path(file_ref)
        if file_path.is_absolute() and file_path.exists():
            return file_path

        # Try relative to codebase root
        codebase_file = self.codebase_path / file_ref
        if codebase_file.exists():
            return codebase_file

        # Try with augmet/ prefix if not present
        if not file_ref.startswith("augmet/"):
            codebase_file = self.codebase_path / "augmet" / file_ref
            if codebase_file.exists():
                return codebase_file

        # Try removing augmet/ prefix if present
        if file_ref.startswith("augmet/"):
            relative_file = file_ref[7:]  # Remove "augmet/" prefix
            codebase_file = self.codebase_path / relative_file
            if codebase_file.exists():
                return codebase_file

        return None

    def _create_branch_name(self, ticket_key: str, summary: str) -> str:
        """Create a branch name from ticket key and summary.

        Uses the same logic as PRCreator to maintain consistency.

        :param ticket_key: Jira ticket key
        :type ticket_key: str
        :param summary: Ticket summary
        :type summary: str
        :return: Branch name
        :rtype: str
        """
        # Clean summary for branch name
        clean_summary = summary.lower()[:50]
        clean_summary = "".join(c if c.isalnum() or c in ("-", "_") else "-" for c in clean_summary)
        clean_summary = "-".join(clean_summary.split())

        # Determine prefix based on ticket type or summary
        prefix = "feature"
        if any(word in summary.lower() for word in ["fix", "bug", "error", "issue"]):
            prefix = "fix"

        # Branch name starts with ticket ID
        branch_name = f"{ticket_key.lower()}/{prefix}-{clean_summary}"
        return branch_name
