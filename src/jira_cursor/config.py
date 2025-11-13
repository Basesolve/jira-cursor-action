"""Configuration management for automation service."""

import os
from typing import Optional

from pydantic import BaseModel, Field


class CursorCloudConfig(BaseModel):
    """Configuration model for Cursor Cloud Agents integration."""

    enabled: bool = Field(
        default=False,
        description="Enable Cursor Cloud Agents code generation",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Cursor Cloud API key",
    )
    base_url: Optional[str] = Field(
        default="https://api.cursor.com",
        description="Base URL for Cursor Cloud API",
    )


class AutomationConfig(BaseModel):
    """Configuration model for automation service."""

    jira_domain: str = Field(..., description="Jira domain (e.g., 'mycompany')")
    jira_email: str = Field(..., description="Jira user email")
    jira_token: str = Field(..., description="Jira API token")
    jira_project_key: str = Field(
        ...,
        description="Jira project key (e.g., 'TS')",  # noqa: E501
    )
    github_repo_owner: str = Field(..., description="GitHub repository owner")
    github_repo_name: str = Field(..., description="GitHub repository name")
    draft_pr_status: str = Field(
        default="Draft PR Creation",
        description="Status name for tickets ready for PR creation",
    )
    need_info_status: str = Field(
        default="Need More Information",
        description="Status name for tickets needing more information",
    )
    pr_created_status: str = Field(
        default="Draft PR created. Pending review",
        description="Status name for tickets after PR is created",
    )
    log_dir: Optional[str] = Field(
        default=None,
        description="Directory for log files (default: ./logs)",
    )
    cursor_cloud: CursorCloudConfig = Field(
        default_factory=CursorCloudConfig,
        description="Cursor Cloud Agents configuration",
    )

    @classmethod
    def from_env(cls) -> "AutomationConfig":
        """Create configuration from environment variables.

        :return: Configuration instance
        :rtype: AutomationConfig
        """
        return cls(
            jira_domain=os.getenv("JIRA_DOMAIN", ""),
            jira_email=os.getenv("JIRA_EMAIL", ""),
            jira_token=os.getenv("JIRA_TOKEN", ""),
            jira_project_key=os.getenv("JIRA_PROJECT_KEY", ""),
            github_repo_owner=os.getenv("GITHUB_REPO_OWNER", ""),
            github_repo_name=os.getenv("GITHUB_REPO_NAME", ""),
            draft_pr_status=os.getenv("DRAFT_PR_STATUS", "Draft PR Creation"),
            need_info_status=os.getenv("NEED_INFO_STATUS", "Need More Information"),
            pr_created_status=os.getenv("PR_CREATED_STATUS", "Draft PR created. Pending review"),
            log_dir=os.getenv("LOG_DIR", None),
            cursor_cloud=CursorCloudConfig(
                enabled=True,  # Always enabled
                api_key=os.getenv("CURSOR_CLOUD_API_KEY", None),
                base_url=os.getenv("CURSOR_CLOUD_BASE_URL", "https://api.cursor.com"),
            ),
        )
