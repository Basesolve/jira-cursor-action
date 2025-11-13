"""Jira API client for querying and updating tickets."""

import json
import logging
from typing import Any, Optional, Union

import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException, Timeout

# Configure logger
logger = logging.getLogger(__name__)

# Using lazy formatting for logging (PYL-W1201, PYL-W1202, PYL-W1203)


class JiraClient:
    """Client for interacting with Jira API."""

    def __init__(
        self,
        domain: str,
        email: str,
        token: str,
        timeout: int = 60,
    ):
        """Initialize Jira client.

        :param domain: Jira domain
            (e.g., 'mycompany' for mycompany.atlassian.net)
        :type domain: str
        :param email: Jira user email
        :type email: str
        :param token: Jira API token
        :type token: str
        :param timeout: Request timeout in seconds
        :type timeout: int
        """
        self.domain = domain
        self.base_url = f"https://{domain}.atlassian.net/rest/api/3"
        self.auth = HTTPBasicAuth(email, token)
        self.timeout = timeout
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        logger.info("Initialized Jira client for domain: %s", domain)

    def get_tickets_by_status(
        self,
        project_key: str,
        status: str,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """Get tickets by status from a project.

        :param project_key: Jira project key (e.g., 'TS')
        :type project_key: str
        :param status: Status name to filter by
        :type status: str
        :param max_results: Maximum number of results to return
        :type max_results: int
        :return: list of ticket dictionaries
        :rtype: list[dict[str, Any]]
        """
        jql = f'project = {project_key} AND status = "{status}" ORDER BY updated DESC'
        # Use the new /search/jql endpoint (migrated from deprecated /search)
        # According to CHANGE-2046, the new endpoint uses GET with query params
        # The new API only returns issue ID by default - must specify fields
        url = f"{self.base_url}/search/jql"
        # Request essential fields: key, summary, description, status, labels,
        # issuetype, components
        fields_param = "key,summary,description,status,labels,issuetype,components"
        params: dict[str, Union[str, int]] = {
            "jql": jql,
            "maxResults": max_results,
            "fields": fields_param,
        }

        try:
            logger.info(
                f"Querying Jira for tickets with status '{status}' in project '{project_key}'"
            )
            logger.debug("JQL query: %s", jql)
            response = requests.get(
                url,
                headers=self.headers,
                auth=self.auth,
                params=params,
                timeout=self.timeout,
            )
            # Log response details for debugging
            if not response.ok:
                error_text = response.text[:500]
                logger.error(f"Jira API error: {response.status_code} - {error_text}")
            response.raise_for_status()
            data = response.json()
            tickets = self._parse_search_response(data)
            logger.info("Found %d tickets with status '%s'", len(tickets), status)
            return tickets
        except Timeout as exc:
            logger.error("Timeout while querying Jira tickets: %s", exc)
            raise
        except RequestException as exc:
            # Log full error details including response body if available
            if hasattr(exc, "response") and exc.response is not None:
                try:
                    error_body = exc.response.text[:1000]
                    logger.error(
                        "Error querying Jira tickets: %s. Response body: %s",
                        exc,
                        error_body,
                    )
                except AttributeError:
                    # Response object may not have text attribute
                    logger.error("Error querying Jira tickets: %s", exc)
            else:
                logger.error("Error querying Jira tickets: %s", exc)
            raise
        except json.JSONDecodeError as exc:
            logger.error("Error parsing Jira response: %s", exc)
            raise

    def get_tickets_by_label(
        self,
        project_key: str,
        label: str,
        status: Optional[str] = None,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """Get tickets by label from a project, optionally filtered by status.

        :param project_key: Jira project key (e.g., 'TS')
        :type project_key: str
        :param label: Label name to filter by
        :type label: str
        :param status: Optional status name to filter by
        :type status: Optional[str]
        :param max_results: Maximum number of results to return
        :type max_results: int
        :return: list of ticket dictionaries
        :rtype: list[dict[str, Any]]
        """
        # Build JQL query with label filter
        jql = f'project = {project_key} AND labels = "{label}"'
        if status:
            jql += f' AND status = "{status}"'
        jql += " ORDER BY updated DESC"

        # Use the new /search/jql endpoint (migrated from deprecated /search)
        # According to CHANGE-2046, the new endpoint uses GET with query params
        # The new API only returns issue ID by default - must specify fields
        url = f"{self.base_url}/search/jql"
        # Request essential fields: key, summary, description, status, labels,
        # issuetype, components
        fields_param = "key,summary,description,status,labels,issuetype,components"
        params: dict[str, Union[str, int]] = {
            "jql": jql,
            "maxResults": max_results,
            "fields": fields_param,
        }

        try:
            logger.info(
                f"Querying Jira for tickets with label '{label}' "
                f"in project '{project_key}'" + (f" and status '{status}'" if status else "")
            )
            logger.debug("JQL query: %s", jql)
            response = requests.get(
                url,
                headers=self.headers,
                auth=self.auth,
                params=params,
                timeout=self.timeout,
            )
            # Log response details for debugging
            if not response.ok:
                error_text = response.text[:500]
                logger.error(f"Jira API error: {response.status_code} - {error_text}")
            response.raise_for_status()
            data = response.json()
            tickets = self._parse_search_response(data)
            logger.info(
                f"Found {len(tickets)} tickets with label '{label}'"
                + (f" and status '{status}'" if status else "")
            )
            return tickets
        except Timeout as exc:
            logger.error("Timeout while querying Jira tickets: %s", exc)
            raise
        except RequestException as exc:
            # Log full error details including response body if available
            if hasattr(exc, "response") and exc.response is not None:
                try:
                    error_body = exc.response.text[:1000]
                    logger.error(
                        "Error querying Jira tickets: %s. Response body: %s",
                        exc,
                        error_body,
                    )
                except AttributeError:
                    # Response object may not have text attribute
                    logger.error("Error querying Jira tickets: %s", exc)
            else:
                logger.error("Error querying Jira tickets: %s", exc)
            raise
        except json.JSONDecodeError as exc:
            logger.error("Error parsing Jira response: %s", exc)
            raise

    def get_tickets_by_jql(
        self,
        jql: str,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """Get tickets using a custom JQL query.

        :param jql: Jira Query Language (JQL) query string
        :type jql: str
        :param max_results: Maximum number of results to return
        :type max_results: int
        :return: list of ticket dictionaries
        :rtype: list[dict[str, Any]]
        """
        # Use the new /search/jql endpoint (migrated from deprecated /search)
        # According to CHANGE-2046, the new endpoint uses GET with query params
        # The new API only returns issue ID by default - must specify fields
        url = f"{self.base_url}/search/jql"
        # Request essential fields: key, summary, description, status, labels,
        # issuetype, components
        fields_param = "key,summary,description,status,labels,issuetype,components"
        params: dict[str, Union[str, int]] = {
            "jql": jql,
            "maxResults": max_results,
            "fields": fields_param,
        }

        try:
            logger.info("Querying Jira with custom JQL query: %s", jql)
            response = requests.get(
                url,
                headers=self.headers,
                auth=self.auth,
                params=params,
                timeout=self.timeout,
            )
            # Log response details for debugging
            if not response.ok:
                error_text = response.text[:500]
                logger.error(f"Jira API error: {response.status_code} - {error_text}")
            response.raise_for_status()
            data = response.json()
            tickets = self._parse_search_response(data)
            logger.info("Found %d tickets with custom JQL query", len(tickets))
            return tickets
        except Timeout as exc:
            logger.error("Timeout while querying Jira tickets: %s", exc)
            raise
        except RequestException as exc:
            # Log full error details including response body if available
            if hasattr(exc, "response") and exc.response is not None:
                try:
                    error_body = exc.response.text[:1000]
                    logger.error(
                        "Error querying Jira tickets: %s. Response body: %s",
                        exc,
                        error_body,
                    )
                except AttributeError:
                    # Response object may not have text attribute
                    logger.error("Error querying Jira tickets: %s", exc)
            else:
                logger.error("Error querying Jira tickets: %s", exc)
            raise
        except json.JSONDecodeError as exc:
            logger.error("Error parsing Jira response: %s", exc)
            raise

    def _parse_search_response(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse Jira search API response.

        :param data: Response data from Jira API
        :type data: dict[str, Any]
        :return: list of ticket dictionaries
        :rtype: list[dict[str, Any]]
        """
        # The new /search/jql endpoint returns data in "values" array
        # Check for both possible response formats for compatibility
        if "values" in data:
            tickets = data.get("values", [])
        elif "issues" in data:
            # Fallback to old format if present
            tickets = data.get("issues", [])
        else:
            # Unexpected structure - log for debugging
            logger.warning(
                f"Unexpected response structure from Jira API. "
                f"Top-level keys: {list(data.keys())[:10]}"
            )
            tickets = []

        # Verify ticket structure and log for debugging
        if tickets and len(tickets) > 0:
            first_ticket = tickets[0]
            # Check if ticket has expected structure
            if "key" not in first_ticket:
                logger.warning(
                    f"Ticket missing 'key' field. Available keys: {list(first_ticket.keys())[:10]}"
                )
            else:
                ticket_key = first_ticket.get("key")
                logger.debug("Successfully retrieved ticket: %s", ticket_key)

        return tickets

    def get_ticket(self, ticket_key: str) -> Optional[dict[str, Any]]:
        """Get a specific ticket by key.

        :param ticket_key: Ticket key (e.g., 'TS-123')
        :type ticket_key: str
        :return: Ticket dictionary or None if not found
        :rtype: Optional[dict[str, Any]]
        """
        url = f"{self.base_url}/issue/{ticket_key}"

        try:
            logger.info("Fetching ticket: %s", ticket_key)
            response = requests.get(
                url,
                headers=self.headers,
                auth=self.auth,
                timeout=self.timeout,
            )
            if response.status_code == 404:
                logger.warning("Ticket %s not found", ticket_key)
                return None
            response.raise_for_status()
            ticket = response.json()
            logger.info("Successfully fetched ticket: %s", ticket_key)
            return ticket
        except Timeout as exc:
            logger.error("Timeout while fetching ticket %s: %s", ticket_key, exc)
            raise
        except RequestException as exc:
            logger.error("Error fetching ticket %s: %s", ticket_key, exc)
            raise
        except json.JSONDecodeError as exc:
            logger.error(
                "Error parsing Jira response for ticket %s: %s",
                ticket_key,
                exc,
            )
            raise

    def get_ticket_attachments(self, ticket_key: str) -> list[dict[str, Any]]:
        """Get attachments for a ticket.

        :param ticket_key: Ticket key (e.g., 'TS-123')
        :type ticket_key: str
        :return: list of attachment dictionaries
        :rtype: list[dict[str, Any]]
        """
        url = f"{self.base_url}/issue/{ticket_key}"
        params = {"fields": "attachment"}

        try:
            logger.info("Fetching attachments for ticket: %s", ticket_key)
            response = requests.get(
                url,
                headers=self.headers,
                auth=self.auth,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            ticket = response.json()
            attachments = ticket.get("fields", {}).get("attachment", [])
            logger.info(f"Found {len(attachments)} attachment(s) for ticket {ticket_key}")
            return attachments
        except Timeout as exc:
            logger.error(f"Timeout while fetching attachments for ticket {ticket_key}: {exc}")
            return []
        except RequestException as exc:
            logger.error(f"Error fetching attachments for ticket {ticket_key}: {exc}")
            return []
        except json.JSONDecodeError as exc:
            logger.error(f"Error parsing Jira response for ticket {ticket_key} attachments: {exc}")
            return []

    def download_attachment(self, attachment_id: str, attachment_url: str) -> Optional[str]:
        """Download attachment content from Jira.

        :param attachment_id: Attachment ID
        :type attachment_id: str
        :param attachment_url: URL to download attachment content
        :type attachment_url: str
        :return: Attachment content as string, or None if failed
        :rtype: Optional[str]
        """
        try:
            logger.info("Downloading attachment %s from Jira", attachment_id)
            response = requests.get(
                attachment_url,
                headers=self.headers,
                auth=self.auth,
                timeout=self.timeout,
            )
            response.raise_for_status()

            # Try to decode as text (for code files)
            try:
                content = response.text
                logger.info(f"Downloaded attachment {attachment_id} ({len(content)} chars)")
                return content
            except UnicodeDecodeError:
                # If not text, return None (binary files not supported)
                logger.warning(f"Attachment {attachment_id} appears to be binary, skipping")
                return None

        except Timeout as exc:
            logger.error(
                "Timeout while downloading attachment %s: %s",
                attachment_id,
                exc,
            )
            return None
        except RequestException as exc:
            logger.error("Error downloading attachment %s: %s", attachment_id, exc)
            return None

    def update_ticket_status(
        self,
        ticket_key: str,
        status_name: str,
    ) -> bool:
        """Update ticket status.

        :param ticket_key: Ticket key (e.g., 'TS-123')
        :type ticket_key: str
        :param status_name: New status name
        :type status_name: str
        :return: True if successful, False otherwise
        :rtype: bool
        """
        # First, get available transitions for the ticket
        transitions_url = f"{self.base_url}/issue/{ticket_key}/transitions"
        try:
            logger.info("Getting transitions for ticket: %s", ticket_key)
            response = requests.get(
                transitions_url,
                headers=self.headers,
                auth=self.auth,
                timeout=self.timeout,
            )
            response.raise_for_status()
            transitions_data = response.json()
            transitions = transitions_data.get("transitions", [])

            # Find the transition that matches the target status
            target_transition = None
            for transition in transitions:
                if transition.get("to", {}).get("name", "").lower() == status_name.lower():
                    target_transition = transition
                    break

            if not target_transition:
                logger.warning(
                    f"No transition found to status '{status_name}' "
                    f"for ticket {ticket_key}. Available transitions: "
                    f"{[t.get('to', {}).get('name') for t in transitions]}"
                )
                return False

            # Execute the transition
            transition_id = target_transition.get("id")
            payload = {"transition": {"id": transition_id}}

            logger.info(f"Updating ticket {ticket_key} to status '{status_name}'")
            response = requests.post(
                transitions_url,
                headers=self.headers,
                auth=self.auth,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.info(f"Successfully updated ticket {ticket_key} to status '{status_name}'")
            return True
        except Timeout as exc:
            logger.error("Timeout while updating ticket %s: %s", ticket_key, exc)
            return False
        except RequestException as exc:
            logger.error("Error updating ticket %s: %s", ticket_key, exc)
            return False
        except json.JSONDecodeError as exc:
            logger.error(
                "Error parsing Jira response for ticket %s: %s",
                ticket_key,
                exc,
            )
            return False

    def add_comment(
        self,
        ticket_key: str,
        comment: str,
    ) -> bool:
        """Add a comment to a ticket.

        :param ticket_key: Ticket key (e.g., 'TS-123')
        :type ticket_key: str
        :param comment: Comment text
        :type comment: str
        :return: True if successful, False otherwise
        :rtype: bool
        """
        url = f"{self.base_url}/issue/{ticket_key}/comment"
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}],
                    }
                ],
            }
        }

        try:
            logger.info("Adding comment to ticket: %s", ticket_key)
            response = requests.post(
                url,
                headers=self.headers,
                auth=self.auth,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.info("Successfully added comment to ticket %s", ticket_key)
            return True
        except Timeout as exc:
            logger.error(
                "Timeout while adding comment to ticket %s: %s",
                ticket_key,
                exc,
            )
            return False
        except RequestException as exc:
            logger.error("Error adding comment to ticket %s: %s", ticket_key, exc)
            return False
