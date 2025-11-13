"""Run the automation service."""

import logging
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from src.jira_cursor.automation_service import create_automation_service, setup_logging

# Configure logger
logger = logging.getLogger(__name__)

JIRA_DOMAIN = os.environ.get("JIRA_DOMAIN", "org")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "dev@org.com")
JIRA_TOKEN = os.environ.get("JIRA_TOKEN", "1234567890")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "1234567890")
GITHUB_REPO_OWNER = os.environ.get("GITHUB_REPO_OWNER", "org")
GITHUB_REPO_NAME = os.environ.get("GITHUB_REPO_NAME", "repo")
NEED_INFO_STATUS = os.environ.get("NEED_INFO_STATUS", "Need More Information")
PR_CREATED_STATUS = os.environ.get("PR_CREATED_STATUS", "Draft PR created. Pending review")

CURSOR_CLOUD_BASE_URL = os.environ.get("CURSOR_CLOUD_BASE_URL", "https://api.cursor.com")
CURSOR_CLOUD_API_KEY = os.environ.get("CURSOR_CLOUD_API_KEY", "1234567890")
CURSOR_CLOUD_REPOSITORY_REF = os.environ.get("CURSOR_CLOUD_REPOSITORY_REF", "main")
CODEBASE_PATH = os.environ.get("CODEBASE_PATH", "")
JQL_QUERY = os.environ.get("JQL_QUERY", "")

if __name__ == "__main__":
    # Set environment variables for create_automation_service
    # (it reads from os.getenv internally)
    os.environ["CURSOR_CLOUD_API_KEY"] = CURSOR_CLOUD_API_KEY
    os.environ["CURSOR_CLOUD_BASE_URL"] = CURSOR_CLOUD_BASE_URL
    os.environ["CURSOR_CLOUD_REPOSITORY_REF"] = CURSOR_CLOUD_REPOSITORY_REF
    if CODEBASE_PATH:
        os.environ["CODEBASE_PATH"] = CODEBASE_PATH

    # Validate required JQL_QUERY
    if not JQL_QUERY:
        print("Error: JQL_QUERY environment variable is required")
        print("Please set JQL_QUERY to a valid JQL query string")
        exit(1)

    # Set up logging
    log_level_str = os.environ.get("LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    setup_logging(log_level=log_level)

    # Log JQL query
    logger.info("JQL Query: %s", JQL_QUERY)

    # Option 1: Let create_automation_service auto-create CodeGenerator
    # (it will use the environment variables we just set)
    service = create_automation_service(
        jira_domain=JIRA_DOMAIN,
        jira_email=JIRA_EMAIL,
        jira_token=JIRA_TOKEN,
        github_repo_owner=GITHUB_REPO_OWNER,
        github_repo_name=GITHUB_REPO_NAME,
        need_info_status=NEED_INFO_STATUS,
        pr_created_status=PR_CREATED_STATUS,
    )

    processed = service.run_once(jql=JQL_QUERY)
    print(f"Processed {processed} tickets")
