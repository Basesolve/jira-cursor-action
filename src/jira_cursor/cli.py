"""Main entry point for automation service."""

import argparse
import logging
import os
import sys

from .automation_service import create_automation_service, setup_logging

# Configure logger
logger = logging.getLogger(__name__)

# Using lazy formatting for logging (PYL-W1201, PYL-W1202, PYL-W1203)


def main() -> int:
    """Main entry point for automation service.

    :return: Exit code (0 for success, non-zero for failure)
    :rtype: int
    """
    parser = argparse.ArgumentParser(
        description="Automated PR creation from Jira tickets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--jira-domain",
        type=str,
        help="Jira domain (e.g., 'mycompany')",
        default=os.getenv("JIRA_DOMAIN", ""),
    )
    parser.add_argument(
        "--jira-email",
        type=str,
        help="Jira user email",
        default=os.getenv("JIRA_EMAIL", ""),
    )
    parser.add_argument(
        "--jira-token",
        type=str,
        help="Jira API token",
        default=os.getenv("JIRA_TOKEN", ""),
    )
    parser.add_argument(
        "--jira-project-key",
        type=str,
        help="Jira project key (e.g., 'TS')",
        default=os.getenv("JIRA_PROJECT_KEY", ""),
    )
    parser.add_argument(
        "--github-repo-owner",
        type=str,
        help="GitHub repository owner",
        default=os.getenv("GITHUB_REPO_OWNER", ""),
    )
    parser.add_argument(
        "--github-repo-name",
        type=str,
        help="GitHub repository name",
        default=os.getenv("GITHUB_REPO_NAME", ""),
    )
    parser.add_argument(
        "--draft-pr-status",
        type=str,
        default="Draft PR Creation",
        help="Status name for tickets ready for PR creation",
    )
    parser.add_argument(
        "--need-info-status",
        type=str,
        default="Need More Information",
        help="Status name for tickets needing more information",
    )
    parser.add_argument(
        "--pr-created-status",
        type=str,
        default="Draft PR created. Pending review",
        help="Status name for tickets after PR is created",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default=None,
        help="Directory for log files (default: ./logs)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once instead of continuously",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--cursor-cloud-api-key",
        type=str,
        default=None,
        help="Cursor Cloud API key",
    )
    parser.add_argument(
        "--cursor-cloud-base-url",
        type=str,
        default="https://api.cursor.com",
        help="Base URL for Cursor Cloud API (default: https://api.cursor.com)",
    )
    parser.add_argument(
        "--cursor-cloud-repository-ref",
        type=str,
        default=None,
        help="Repository ref/branch for agent source (default: main)",
    )
    parser.add_argument(
        "--jql-query",
        type=str,
        help="JQL query to select tickets for processing",
        default=os.getenv("JQL_QUERY", ""),
    )

    args = parser.parse_args()

    # Set up logging
    log_level = getattr(logging, args.log_level.upper())
    setup_logging(log_dir=args.log_dir, log_level=log_level)

    # Validate required arguments
    required_args = [
        ("jira_domain", args.jira_domain),
        ("jira_email", args.jira_email),
        ("jira_token", args.jira_token),
        ("jira_project_key", args.jira_project_key),
        ("github_repo_owner", args.github_repo_owner),
        ("github_repo_name", args.github_repo_name),
        ("jql_query", args.jql_query),
    ]

    missing_args = [name for name, value in required_args if not value]
    if missing_args:
        logger.error("Missing required arguments: %s", ", ".join(missing_args))
        logger.error("Please provide these via command line or environment variables")
        return 1

    try:
        # Initialize code generator (Cursor Cloud Agents is always enabled)
        code_generator = None
        cursor_api_key = args.cursor_cloud_api_key or os.getenv("CURSOR_CLOUD_API_KEY", None)

        if cursor_api_key:
            from .code_generator import CodeGenerator

            # Jira client is needed for fetching attachments
            from .jira_client import JiraClient

            jira_client_for_codegen = JiraClient(
                domain=args.jira_domain,
                email=args.jira_email,
                token=args.jira_token,
            )

            # Construct repository URL from GitHub repo info
            repository_url = f"https://github.com/{args.github_repo_owner}/{args.github_repo_name}"
            repository_ref = args.cursor_cloud_repository_ref or os.getenv(
                "CURSOR_CLOUD_REPOSITORY_REF", "main"
            )

            code_generator = CodeGenerator(
                api_key=cursor_api_key,
                jira_client=jira_client_for_codegen,
                base_url=args.cursor_cloud_base_url
                or os.getenv("CURSOR_CLOUD_BASE_URL", "https://api.cursor.com"),
                codebase_path=os.getenv("CODEBASE_PATH", None),
                repository_url=repository_url,
                repository_ref=repository_ref,
            )
            logger.info(
                "Code generator initialized with Cursor Cloud Agents (repository: %s, ref: %s)",
                repository_url,
                repository_ref,
            )

        # Validate that code generator is configured (required)
        if not code_generator:
            logger.error(
                "Code generator (Cursor Cloud Agents) is required but "
                "not configured. Please provide CURSOR_CLOUD_API_KEY."
            )
            return 1

        # Create automation service
        service = create_automation_service(
            jira_domain=args.jira_domain,
            jira_email=args.jira_email,
            jira_token=args.jira_token,
            github_repo_owner=args.github_repo_owner,
            github_repo_name=args.github_repo_name,
            jira_project_key=args.jira_project_key,
            draft_pr_status=args.draft_pr_status,
            need_info_status=args.need_info_status,
            pr_created_status=args.pr_created_status,
            code_generator=code_generator,
        )

        # Run service (always run once for GitHub Actions)
        logger.info("Running automation service once...")
        processed = service.run_once(jql=args.jql_query)
        logger.info("Processed %d tickets", processed)
        return 0

    except KeyboardInterrupt:
        logger.info("Received interrupt signal. Exiting...")
        return 0
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Catching general exception is acceptable here for top-level
        # error handling
        logger.error("Fatal error: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
