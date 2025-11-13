"""Module for assessing Jira tickets to determine if they have enough
information for PR creation.
"""

import logging
import re
from typing import Any, Optional

# Configure logger
logger = logging.getLogger(__name__)

# pylint: disable=logging-fstring-interpolation
# Using f-strings for logging matches codebase style


class TicketAssessor:
    """Assesses Jira tickets to determine if they have enough information.

    Checks if tickets have enough information for PR creation.
    """

    def __init__(self):
        """Initialize the ticket assessor."""
        logger.info("Initialized TicketAssessor")

    def assess_ticket(self, ticket: dict[str, Any]) -> tuple[bool, list[str]]:
        """Assess if a ticket has enough information to create a PR.

        :param ticket: Jira ticket dictionary
        :type ticket: dict[str, Any]
        :return: Tuple of (has_enough_info, missing_fields)
        :rtype: tuple[bool, list[str]]
        """
        missing_fields: list[str] = []
        fields = ticket.get("fields", {})

        # Check for summary
        summary = fields.get("summary", "").strip()
        if not summary:
            missing_fields.append("summary")

        # Check for description
        description = TicketAssessor._extract_text_from_adf(fields.get("description"))
        if not description or len(description.strip()) < 50:
            missing_fields.append("description (minimum 50 characters)")

        # Check for acceptance criteria or similar fields
        # This is a common field in Jira, but field IDs vary
        # We'll check common custom field names
        acceptance_criteria = self._get_custom_field(
            fields, ["Acceptance Criteria", "acceptance_criteria"]
        )
        if not acceptance_criteria:
            # Not critical, but good to have
            logger.debug("No acceptance criteria found (optional)")

        # Check for technical details
        # Look for keywords that indicate technical requirements
        technical_keywords = [
            "file",
            "function",
            "module",
            "class",
            "api",
            "endpoint",
            "database",
            "config",
            "test",
            "implementation",
            "code",
            "fix",
            "bug",
            "feature",
        ]
        has_technical_details = any(
            keyword.lower() in description.lower() for keyword in technical_keywords
        )
        if not has_technical_details:
            missing_fields.append("technical details (implementation requirements)")

        # Check for file paths or module references
        # Look for patterns like file paths, module names, etc.
        file_patterns = [
            r"[a-zA-Z0-9_/]+\.py",
            r"[a-zA-Z0-9_/]+\.yaml",
            r"[a-zA-Z0-9_/]+\.yml",
            r"augmet/[a-zA-Z0-9_/]+",
        ]
        has_file_references = any(
            re.search(pattern, description, re.IGNORECASE) for pattern in file_patterns
        )
        if not has_file_references:
            logger.debug("No file paths or module references found (optional)")

        # Check for labels (optional but helpful)
        labels = fields.get("labels", [])
        if not labels:
            logger.debug("No labels found (optional)")

        # Determine if we have enough information
        # We require at minimum: summary, description, and some technical
        # details
        critical_missing = [
            field for field in missing_fields if "summary" in field or "description" in field
        ]
        has_enough_info = len(critical_missing) == 0 and len(missing_fields) <= 1

        if has_enough_info:
            logger.info(f"Ticket {ticket.get('key')} has enough information for PR creation")
        else:
            logger.warning(
                f"Ticket {ticket.get('key')} is missing required information: {missing_fields}"
            )

        return has_enough_info, missing_fields

    @staticmethod
    def _extract_text_from_adf(  # noqa: C901
        adf_content: Optional[dict[str, Any]],
    ) -> str:
        """Extract plain text from Atlassian Document Format (ADF).

        :param adf_content: ADF content dictionary
        :type adf_content: Optional[dict[str, Any]]
        :return: Extracted plain text
        :rtype: str
        """
        if not adf_content:
            return ""

        text_parts: list[str] = []

        def extract_from_node(node: dict[str, Any]) -> None:
            """Recursively extract text from ADF nodes."""
            if isinstance(node, dict):
                if node.get("type") == "text":
                    text_parts.append(node.get("text", ""))
                elif "content" in node:
                    if isinstance(node["content"], list):
                        for child in node["content"]:
                            extract_from_node(child)
                    else:
                        extract_from_node(node["content"])

        if isinstance(adf_content, dict):
            if "content" in adf_content:
                for node in adf_content.get("content", []):
                    extract_from_node(node)
            else:
                extract_from_node(adf_content)

        return " ".join(text_parts)

    def _get_custom_field(
        self,
        fields: dict[str, Any],
        possible_names: list[str],
    ) -> Optional[str]:
        """Get a custom field by trying multiple possible names.

        :param fields: Ticket fields dictionary
        :type fields: dict[str, Any]
        :param possible_names: List of possible field names to try
        :type possible_names: list[str]
        :return: Field value if found, None otherwise
        :rtype: Optional[str]
        """
        for name in possible_names:
            # Try exact match
            if name in fields:
                value = fields[name]
                if value:
                    return str(value)

            # Try case-insensitive match
            for key, value in fields.items():
                if key.lower() == name.lower() and value:
                    return str(value)

        return None

    def extract_requirements(self, ticket: dict[str, Any]) -> dict[str, Any]:
        """Extract requirements and context from a ticket.

        :param ticket: Jira ticket dictionary
        :type ticket: dict[str, Any]
        :return: Dictionary with extracted requirements
        :rtype: dict[str, Any]
        """
        fields = ticket.get("fields", {})
        summary = fields.get("summary", "")
        description = TicketAssessor._extract_text_from_adf(fields.get("description"))
        labels = fields.get("labels", [])
        ticket_type = fields.get("issuetype", {}).get("name", "")

        # Extract component(s) from ticket
        # Components is typically an array of objects with 'name' field
        components = fields.get("components", [])
        component_names: list[str] = []
        if components:
            for component in components:
                if isinstance(component, dict):
                    component_name = component.get("name", "")
                    if component_name:
                        component_names.append(component_name)
                elif isinstance(component, str):
                    component_names.append(component)
        # Use first component if multiple exist
        component = component_names[0] if component_names else None

        # Extract file paths mentioned in description
        file_patterns = [
            r"[a-zA-Z0-9_/]+\.py",
            r"[a-zA-Z0-9_/]+\.yaml",
            r"[a-zA-Z0-9_/]+\.yml",
            r"augmet/[a-zA-Z0-9_/]+",
        ]
        file_references: list[str] = []
        for pattern in file_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            file_references.extend(matches)

        return {
            "ticket_key": ticket.get("key"),
            "summary": summary,
            "description": description,
            "labels": labels,
            "ticket_type": ticket_type,
            "component": component,
            "components": component_names,
            "file_references": list(set(file_references)),
        }
