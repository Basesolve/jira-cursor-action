"""Main automation service for monitoring Jira tickets and creating PRs."""

import logging
import logging.handlers
import os
import time
from typing import Any, Optional

from .code_generator import CodeGenerator
from .jira_client import JiraClient
from .ticket_assessor import TicketAssessor

# Configure logger
logger = logging.getLogger(__name__)

# Using lazy formatting for logging (PYL-W1201, PYL-W1202, PYL-W1203)

# Prefix for automated comments to distinguish from human comments
AUTOMATED_COMMENT_PREFIX = "[🤖 Automated]"


class AutomationService:  # pylint: disable=too-many-instance-attributes
    """Main service for automating PR creation from Jira tickets."""

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        jira_client: JiraClient,
        ticket_assessor: TicketAssessor,
        need_info_status: str = "Need More Information",
        pr_created_status: str = "Draft PR created. Pending review",
        code_generator: Optional[CodeGenerator] = None,
    ):
        """Initialize automation service.

        :param jira_client: Jira client instance
        :type jira_client: JiraClient
        :param ticket_assessor: Ticket assessor instance
        :type ticket_assessor: TicketAssessor
        :param need_info_status: Status name for tickets needing more info
        :type need_info_status: str
        :param pr_created_status: Status name for tickets after PR is created
        :type pr_created_status: str
        :param code_generator: Code generator for Cursor Cloud Agents
            integration
        :type code_generator: Optional[CodeGenerator]
        """
        self.jira_client = jira_client
        self.ticket_assessor = ticket_assessor
        self.code_generator = code_generator
        self.need_info_status = need_info_status
        self.pr_created_status = pr_created_status
        self.processed_tickets: set[str] = set()
        logger.info("Initialized AutomationService")

    def process_ticket(self, ticket: dict[str, Any]) -> bool:
        """Process a single ticket.

        :param ticket: Jira ticket dictionary
        :type ticket: Dict[str, Any]
        :return: True if processed successfully, False otherwise
        :rtype: bool
        """
        ticket_key = ticket.get("key", "UNKNOWN")
        logger.info("Processing ticket: %s", ticket_key)

        try:
            # Assess ticket
            has_enough_info, missing_fields = self.ticket_assessor.assess_ticket(ticket)

            if not has_enough_info:
                # Update ticket status to "Need More Information"
                logger.warning(
                    "Ticket %s does not have enough information. Missing fields: %s",
                    ticket_key,
                    missing_fields,
                )
                comment = (
                    f"{AUTOMATED_COMMENT_PREFIX} Automated assessment: This "
                    f"ticket does not have enough information to create a "
                    f"draft PR. Missing: {', '.join(missing_fields)}. "
                    f"Please provide the missing information and update the "
                    f"ticket status accordingly."
                )
                self.jira_client.add_comment(ticket_key, comment)
                success = self.jira_client.update_ticket_status(ticket_key, self.need_info_status)
                if success:
                    logger.info(
                        "Updated ticket %s to status '%s'",
                        ticket_key,
                        self.need_info_status,
                    )
                else:
                    logger.error("Failed to update ticket %s status", ticket_key)
                return success

            # Extract requirements
            requirements = self.ticket_assessor.extract_requirements(ticket)
            logger.info("Extracted requirements for ticket %s", ticket_key)

            # Generate code and create PR using Cursor Cloud Agents
            if self.code_generator:
                logger.info("Triggering code generation for ticket %s", ticket_key)
                codebase_context = self.code_generator.analyze_codebase_context(
                    requirements.get("file_references", []), requirements
                )
                result = self.code_generator.generate_code_changes(
                    ticket, requirements, codebase_context
                )
                if result:
                    # Agent completed successfully - PR was created by Cursor
                    status = (
                        result.get("status", "completed")
                        if isinstance(result, dict)
                        else "completed"
                    )
                    pr_url = result.get("pr_url") if isinstance(result, dict) else None

                    logger.info(
                        "Cursor Cloud Agents completed for ticket %s "
                        "(status: %s). PR was created by Cursor.",
                        ticket_key,
                        status,
                    )

                    # Add comment to ticket with PR URL if available
                    if pr_url:
                        comment = (
                            f"{AUTOMATED_COMMENT_PREFIX} Automated PR creation: "
                            f"A draft PR has been created by Cursor Cloud Agents "
                            f"for ticket {ticket_key}.\n\n"
                            f"PR URL: {pr_url}\n\n"
                            f"Please review the PR and update the ticket status "
                            f"accordingly."
                        )
                    else:
                        comment = (
                            f"{AUTOMATED_COMMENT_PREFIX} Automated PR creation: "
                            f"A draft PR has been created by Cursor Cloud Agents "
                            f"for ticket {ticket_key}.\n\n"
                            f"Please review the PR and update the ticket status "
                            f"accordingly."
                        )
                    self.jira_client.add_comment(ticket_key, comment)

                    # Update ticket status to "Draft PR created. Pending review"
                    status_updated = self.jira_client.update_ticket_status(
                        ticket_key, self.pr_created_status
                    )
                    if status_updated:
                        logger.info(
                            "Updated ticket %s to status '%s'",
                            ticket_key,
                            self.pr_created_status,
                        )
                    else:
                        logger.warning(
                            "Failed to update ticket %s to status '%s'",
                            ticket_key,
                            self.pr_created_status,
                        )

                    # Mark ticket as processed
                    self.processed_tickets.add(ticket_key)
                    return True
                else:
                    logger.warning(
                        "No result returned from code generator for ticket %s",
                        ticket_key,
                    )
                    comment = (
                        f"{AUTOMATED_COMMENT_PREFIX} PR creation failed for "
                        f"ticket {ticket_key}. "
                        f"Cursor Cloud Agents did not complete successfully. "
                        f"Please check the logs."
                    )
                    self.jira_client.add_comment(ticket_key, comment)
                    return False
            else:
                logger.error(
                    "Code generator not configured. Cannot process ticket %s.",
                    ticket_key,
                )
                comment = (
                    f"{AUTOMATED_COMMENT_PREFIX} Code generator not "
                    f"configured. "
                    f"Please configure Cursor Cloud Agents to process "
                    f"this ticket."
                )
                self.jira_client.add_comment(ticket_key, comment)
                return False

        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Catching general exception is acceptable here for error handling
            logger.error(
                "Error processing ticket %s: %s",
                ticket_key,
                exc,
                exc_info=True,
            )
            return False

    def run_once(self, jql: str) -> int:
        """Run the automation service once.

        Process tickets selected by the provided JQL query.

        :param jql: JQL query to select tickets
        :type jql: str
        :return: Number of tickets processed
        :rtype: int
        """
        logger.info("Starting automation run")
        try:
            logger.info("Using JQL query to select tickets")
            logger.debug("JQL query: %s", jql)
            all_tickets = self.jira_client.get_tickets_by_jql(
                jql=jql,
                max_results=50,
            )
            logger.info("Found %d tickets with JQL query", len(all_tickets))

            if not all_tickets:
                logger.info("No tickets found with JQL query")
                return 0

            logger.info(
                "Total tickets to process: %d (from JQL query)",
                len(all_tickets),
            )

            # Process each ticket
            processed_count = 0
            for ticket in all_tickets:
                ticket_key = ticket.get("key", "UNKNOWN")
                # Skip if already processed in this session
                if ticket_key in self.processed_tickets:
                    logger.debug("Skipping already processed ticket: %s", ticket_key)
                    continue

                if self.process_ticket(ticket):
                    processed_count += 1
                    # Add a small delay between tickets to avoid rate limiting
                    time.sleep(2)

            logger.info("Processed %d tickets in this run", processed_count)
            return processed_count

        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Catching general exception is acceptable here for error handling
            logger.error("Error in automation run: %s", exc, exc_info=True)
            return 0


def setup_logging(log_dir: Optional[str] = None, log_level: int = logging.INFO) -> None:
    """Set up logging with file rotation.

    :param log_dir: Directory for log files (default: ./logs)
    :type log_dir: Optional[str]
    :param log_level: Logging level (default: INFO)
    :type log_level: int
    """
    if log_dir is None:
        log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "automation_service.log")
    max_bytes = 10 * 1024 * 1024  # 10 MB
    backup_count = 5

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logger.info("Logging configured. Log file: %s", log_file)


def create_automation_service(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    jira_domain: str,
    jira_email: str,
    jira_token: str,
    github_repo_owner: str,
    github_repo_name: str,
    need_info_status: str = "Need More Information",
    pr_created_status: str = "Draft PR created. Pending review",
    code_generator: Optional[CodeGenerator] = None,
) -> AutomationService:
    """Create and configure an automation service instance.

    :param jira_domain: Jira domain
    :type jira_domain: str
    :param jira_email: Jira user email
    :type jira_email: str
    :param jira_token: Jira API token
    :type jira_token: str
    :param github_repo_owner: GitHub repository owner
    :type github_repo_owner: str
    :param github_repo_name: GitHub repository name
    :type github_repo_name: str
    :param need_info_status: Status name for tickets needing more information
    :type need_info_status: str
    :param code_generator: Code generator instance (required)
    :type code_generator: Optional[CodeGenerator]
    :return: Configured automation service
    :rtype: AutomationService
    """
    jira_client = JiraClient(
        domain=jira_domain,
        email=jira_email,
        token=jira_token,
    )

    ticket_assessor = TicketAssessor()

    # Initialize code generator if not provided (Cursor Cloud Agents is always enabled)
    if code_generator is None:
        # Try to create from environment/config
        cursor_api_key = os.getenv("CURSOR_CLOUD_API_KEY", None)
        if cursor_api_key:
            from .code_generator import CodeGenerator

            # Construct repository URL from GitHub repo info
            repository_url = f"https://github.com/{github_repo_owner}/{github_repo_name}"
            repository_ref = os.getenv("CURSOR_CLOUD_REPOSITORY_REF", "main")

            code_generator = CodeGenerator(
                api_key=cursor_api_key,
                jira_client=jira_client,
                base_url=os.getenv("CURSOR_CLOUD_BASE_URL", "https://api.cursor.com"),
                codebase_path=os.getenv("CODEBASE_PATH", None),
                repository_url=repository_url,
                repository_ref=repository_ref,
            )
            logger.info(
                "Code generator initialized with Cursor Cloud Agents (repository: %s, ref: %s)",
                repository_url,
                repository_ref,
            )

    service = AutomationService(
        jira_client=jira_client,
        ticket_assessor=ticket_assessor,
        need_info_status=need_info_status,
        pr_created_status=pr_created_status,
        code_generator=code_generator,
    )

    return service
