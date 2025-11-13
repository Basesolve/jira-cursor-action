"""Jira to Cursor Cloud Agent automation package.

This package enables automated PR creation from Jira tickets
using Cursor Cloud Agents.
"""

__version__ = "0.1.1"

from .automation_service import (
    AutomationService,
    create_automation_service,
    setup_logging,
)
from .code_generator import CodeGenerator
from .config import AutomationConfig, CursorCloudConfig
from .cursor_cloud_client import CursorCloudClient
from .jira_client import JiraClient
from .ticket_assessor import TicketAssessor

__all__ = [
    "__version__",
    "AutomationService",
    "AutomationConfig",
    "CodeGenerator",
    "CursorCloudClient",
    "CursorCloudConfig",
    "JiraClient",
    "TicketAssessor",
    "create_automation_service",
    "setup_logging",
]
