# jira-cursor

[![PyPI version](https://badge.fury.io/py/jira-cursor.svg)](https://badge.fury.io/py/jira-cursor)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Automate PR creation from Jira tickets using Cursor Cloud Agents. This package monitors Jira tickets and automatically generates code changes and creates draft pull requests based on ticket requirements.

## Features

- **Automatic Ticket Monitoring**: Polls Jira for tickets with "Draft PR Creation" status or "cursor" label
- **Intelligent Ticket Assessment**: Evaluates if tickets have enough information to create a PR
- **Automated Code Generation**: Uses Cursor Cloud Agents to generate code changes based on ticket requirements
- **PR Creation**: Automatically creates draft PRs on GitHub with generated code
- **Status Management**:
  - Updates Jira ticket status to "Need More Information" when required
  - Updates Jira ticket status to "Draft PR created. Pending review" after PR creation
- **Comprehensive Logging**: File rotation and console logging

## Installation

### From PyPI (Recommended)

```bash
pip install jira-cursor
```

### From Source

```bash
git clone https://github.com/your-org/jira-cursor-action.git
cd jira-cursor-action
pip install -e .
# Or using uv (recommended for faster installs)
uv pip install -e .
```

## Quick Start

### 1. Install the Package

```bash
pip install jira-cursor
```

### 2. Set Environment Variables

```bash
export JIRA_DOMAIN="your-company"
export JIRA_EMAIL="your-email@example.com"
export JIRA_TOKEN="your-jira-api-token"
export JIRA_PROJECT_KEY="TS"
export GITHUB_REPO_OWNER="your-org"
export GITHUB_REPO_NAME="your-repo"
export CURSOR_CLOUD_API_KEY="your-cursor-cloud-api-key"  # Required
export JQL_QUERY='project = TS AND status = "Draft PR Creation"'  # Required
```

### 3. Run the CLI

```bash
jira-cursor --once --jql-query 'project = TS AND status = "Draft PR Creation"'
```

Or using the run script:

```bash
python run.py
```

## Usage

### Command Line Interface

The package provides a `jira-cursor` CLI command:

```bash
jira-cursor [OPTIONS]
```

#### Basic Usage

```bash
# Run once (process all tickets and exit)
jira-cursor --once --jql-query 'project = TS AND status = "Draft PR Creation"'

# Run with all required options
jira-cursor \
  --jira-domain "your-company" \
  --jira-email "your-email@example.com" \
  --jira-token "your-jira-api-token" \
  --jira-project-key "TS" \
  --github-repo-owner "your-org" \
  --github-repo-name "your-repo" \
  --cursor-cloud-api-key "your-cursor-api-key" \
  --jql-query 'project = TS AND status = "Draft PR Creation"'
```

#### Command Line Options

| Option                          | Environment Variable          | Description                                 | Default                            |
| ------------------------------- | ----------------------------- | ------------------------------------------- | ---------------------------------- |
| `--jira-domain`                 | `JIRA_DOMAIN`                 | Jira domain (e.g., 'mycompany')             | Required                           |
| `--jira-email`                  | `JIRA_EMAIL`                  | Jira user email                             | Required                           |
| `--jira-token`                  | `JIRA_TOKEN`                  | Jira API token                              | Required                           |
| `--jira-project-key`            | `JIRA_PROJECT_KEY`            | Jira project key (e.g., 'TS')               | Required                           |
| `--github-repo-owner`           | `GITHUB_REPO_OWNER`           | GitHub repository owner                     | Required                           |
| `--github-repo-name`            | `GITHUB_REPO_NAME`            | GitHub repository name                      | Required                           |
| `--cursor-cloud-api-key`        | `CURSOR_CLOUD_API_KEY`        | Cursor Cloud API key (required)             | Required                           |
| `--jql-query`                   | `JQL_QUERY`                   | JQL query to select tickets for processing  | Required                           |
| `--cursor-cloud-base-url`       | `CURSOR_CLOUD_BASE_URL`       | Cursor Cloud API base URL                   | `https://api.cursor.com`           |
| `--cursor-cloud-repository-ref` | `CURSOR_CLOUD_REPOSITORY_REF` | Repository ref/branch                       | `main`                             |
| `--draft-pr-status`             | `DRAFT_PR_STATUS`             | Status name for tickets ready for PR        | `Draft PR Creation`                |
| `--need-info-status`            | `NEED_INFO_STATUS`            | Status name for tickets needing info        | `Need More Information`            |
| `--pr-created-status`           | `PR_CREATED_STATUS`           | Status after PR creation                    | `Draft PR created. Pending review` |
| `--log-dir`                     | `LOG_DIR`                     | Directory for log files                     | `./logs`                           |
| `--log-level`                   | -                             | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO`                             |
| `--once`                        | -                             | Run once instead of continuously            | False                              |

### Python API

You can also use the package programmatically:

```python
from jira_cursor import (
    create_automation_service,
    CodeGenerator,
    JiraClient,
    setup_logging,
)

# Set up logging
setup_logging(log_level=logging.INFO)

# Create code generator
jira_client = JiraClient(
    domain="your-company",
    email="your-email@example.com",
    token="your-jira-token",
)

code_generator = CodeGenerator(
    api_key="your-cursor-api-key",
    jira_client=jira_client,
    repository_url="https://github.com/your-org/your-repo",
    repository_ref="main",
)

# Create automation service
service = create_automation_service(
    jira_domain="your-company",
    jira_email="your-email@example.com",
    jira_token="your-jira-token",
    github_repo_owner="your-org",
    github_repo_name="your-repo",
    jira_project_key="TS",
    code_generator=code_generator,
)

# Process tickets with JQL query (required)
jql_query = 'project = TS AND status = "Draft PR Creation"'
processed_count = service.run_once(jql=jql_query)
print(f"Processed {processed_count} tickets")
```

## How It Works

1. **Ticket Selection**: The service uses a JQL (Jira Query Language) query to select tickets for processing. You must provide a `JQL_QUERY` that identifies the tickets you want to process (e.g., `project = TS AND status = "Draft PR Creation"`).

2. **Ticket Assessment**: Each selected ticket is assessed to determine if it has enough information:

   - Summary (required)
   - Description with at least 50 characters (required)
   - Technical details or implementation requirements (required)
   - File references (optional but helpful)

3. **Code Generation**: If a ticket has enough information:

   - Cursor Cloud Agents analyzes the ticket requirements
   - Code changes are generated based on the ticket
   - A branch is created automatically by Cursor Cloud Agents
   - A draft pull request is created with the generated code

4. **PR Creation**:

   - Cursor Cloud Agents automatically creates a draft PR on GitHub with the generated code
   - A comment is added to the Jira ticket with the PR link (if available)
   - The ticket status is updated to "Draft PR created. Pending review"

5. **Status Update**: If a ticket doesn't have enough information:
   - A comment is added explaining what's missing
   - The ticket status is updated to "Need More Information"

## Ticket Assessment Criteria

A ticket is considered to have enough information if it has:

- **Summary**: A non-empty summary
- **Description**: At least 50 characters of description
- **Technical Details**: Contains keywords indicating technical requirements (e.g., "file", "function", "module", "api", "implementation", etc.)

Optional but helpful:

- File paths or module references
- Acceptance criteria
- Labels

## Configuration

### Environment Variables

All configuration can be provided via environment variables:

```bash
# Jira Configuration
export JIRA_DOMAIN="your-company"
export JIRA_EMAIL="your-email@example.com"
export JIRA_TOKEN="your-jira-api-token"
export JIRA_PROJECT_KEY="TS"

# GitHub Configuration
export GITHUB_REPO_OWNER="your-org"
export GITHUB_REPO_NAME="your-repo"

# Cursor Cloud Configuration
export CURSOR_CLOUD_API_KEY="your-cursor-cloud-api-key"  # Required
export CURSOR_CLOUD_BASE_URL="https://api.cursor.com"  # Optional
export CURSOR_CLOUD_REPOSITORY_REF="main"  # Optional

# Local File Resolution (Optional)
export CODEBASE_PATH="/path/to/codebase"  # Optional, for local file resolution

# JQL Query (Required)
export JQL_QUERY='project = TS AND status = "Draft PR Creation"'

# Status Configuration (Optional)
export DRAFT_PR_STATUS="Draft PR Creation"
export NEED_INFO_STATUS="Need More Information"
export PR_CREATED_STATUS="Draft PR created. Pending review"

# Logging Configuration (Optional)
export LOG_DIR="./logs"
```

### Using Pydantic Config

You can also use the `AutomationConfig` class for type-safe configuration:

```python
from jira_cursor import AutomationConfig

config = AutomationConfig.from_env()
# Or create manually
config = AutomationConfig(
    jira_domain="your-company",
    jira_email="your-email@example.com",
    jira_token="your-jira-token",
    jira_project_key="TS",
    github_repo_owner="your-org",
    github_repo_name="your-repo",
)
```

Note: The `AutomationConfig` class does not include the `JQL_QUERY` parameter, which must be provided separately when calling `run_once()`.

## Deployment Options

### GitHub Actions

Create `.github/workflows/jira-pr-automation.yml`:

```yaml
name: Jira PR Automation

on:
  schedule:
    - cron: "*/5 * * * *" # Every 5 minutes
  workflow_dispatch:

jobs:
  automate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.9"

      - name: Install jira-cursor
        run: pip install jira-cursor

      - name: Run automation
        env:
          JIRA_DOMAIN: ${{ secrets.JIRA_DOMAIN }}
          JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
          JIRA_TOKEN: ${{ secrets.JIRA_TOKEN }}
          JIRA_PROJECT_KEY: ${{ secrets.JIRA_PROJECT_KEY }}
          GITHUB_REPO_OWNER: ${{ secrets.GITHUB_REPO_OWNER }}
          GITHUB_REPO_NAME: ${{ secrets.GITHUB_REPO_NAME }}
          CURSOR_CLOUD_API_KEY: ${{ secrets.CURSOR_CLOUD_API_KEY }}
          JQL_QUERY: ${{ secrets.JQL_QUERY }}
        run: jira-cursor --once
```

### Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app

RUN pip install jira-cursor

CMD ["jira-cursor"]
```

### Systemd Service

```ini
[Unit]
Description=Jira to PR Automation Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/opt/jira-automation
EnvironmentFile=/opt/jira-automation/.env
ExecStart=/usr/local/bin/jira-cursor
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Logging

Logs are written to:

- **Console**: stdout/stderr
- **Rotating log file**: `logs/automation_service.log` (default)

Log files are rotated when they reach 10 MB, keeping up to 5 backup files.

Set log level:

```bash
jira-cursor --log-level DEBUG
```

## Requirements

- Python 3.8+
- Jira API token with read/write permissions
- Cursor Cloud API key (required)
- Access to the Jira project and GitHub repository
- A valid JQL query to select tickets for processing (required)

## Security Considerations

- **Never commit tokens or credentials**: Use environment variables or secure configuration management
- **Use least privilege tokens**: Grant only necessary permissions
- **Rotate tokens regularly**: Follow your organization's token rotation policy
- **Review PRs before merging**: All PRs are created as drafts for review

## Troubleshooting

### No tickets found

- Verify your JQL query is correct and matches tickets in your project
- Test your JQL query directly in Jira to ensure it returns results
- Check that tickets exist matching your query criteria
- Verify Jira API credentials and permissions
- Ensure the JQL query is properly escaped when passed as an environment variable

### PR creation fails

- Check that the repository exists and is accessible
- Verify Cursor Cloud API key has necessary permissions
- Ensure branch names don't conflict with existing branches
- Check Cursor Cloud API logs for errors

### Status update fails

- Verify the target status exists in your Jira workflow
- Check that the Jira user has permission to transition tickets
- Ensure the status name matches exactly (case-sensitive)

## API Reference

### Main Classes

- `AutomationService`: Main service for automating PR creation
- `JiraClient`: Client for interacting with Jira API
- `CodeGenerator`: Generates code changes using Cursor Cloud Agents
- `CursorCloudClient`: Client for Cursor Cloud Agents API
- `TicketAssessor`: Assesses Jira tickets for completeness
- `AutomationConfig`: Configuration model using Pydantic

### Functions

- `create_automation_service()`: Factory function to create an AutomationService
- `setup_logging()`: Configure logging with file rotation

See the [API documentation](https://github.com/your-org/jira-cursor-action) for detailed API reference.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## JQL Query Examples

The `JQL_QUERY` parameter is required and determines which tickets are processed. Here are some example queries:

```bash
# Process tickets with specific status
export JQL_QUERY='project = TS AND status = "Draft PR Creation"'

# Process tickets with a label
export JQL_QUERY='project = TS AND labels = cursor'

# Process tickets assigned to a user
export JQL_QUERY='project = TS AND assignee = currentUser() AND status = "Draft PR Creation"'

# Process tickets created in the last 7 days
export JQL_QUERY='project = TS AND created >= -7d AND status = "Draft PR Creation"'

# Combine multiple conditions
export JQL_QUERY='project = TS AND (status = "Draft PR Creation" OR labels = cursor)'
```

For more information on JQL syntax, see the [Jira JQL documentation](https://support.atlassian.com/jira-service-management-cloud/docs/use-advanced-search-with-jira-query-language-jql/).

## Support

For issues, questions, or contributions, please open an issue on [GitHub](https://github.com/your-org/jira-cursor-action/issues).
