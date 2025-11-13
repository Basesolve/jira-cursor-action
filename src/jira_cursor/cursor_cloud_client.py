"""Cursor Cloud Agents API client for code generation."""

import json
import logging
import random
import time
from typing import Any, Optional

import requests
from requests.exceptions import RequestException, Timeout

# Configure logger
logger = logging.getLogger(__name__)

# Using lazy formatting for logging (PYL-W1201, PYL-W1202, PYL-W1203)


class CursorCloudClient:
    """Client for interacting with Cursor Cloud Agents API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.cursor.com",
        repository_url: Optional[str] = None,
        repository_ref: Optional[str] = None,
    ):
        """Initialize Cursor Cloud Agents client.

        :param api_key: Cursor Cloud API key
        :type api_key: str
        :param base_url: Base URL for Cursor Cloud API
        :type base_url: str
        :param repository_url: Optional repository URL for source
        :type repository_url: Optional[str]
        :param repository_ref: Optional repository ref (branch/commit)
        :type repository_ref: Optional[str]
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.repository_url = repository_url
        self.repository_ref = repository_ref or "main"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        logger.info("Initialized CursorCloudClient with base URL: %s", self.base_url)

    def generate_code(
        self,
        prompt: str,
        context: Optional[str] = None,
        file_references: Optional[list[str]] = None,
        codebase_context: Optional[str] = None,
        file_contents: Optional[dict[str, str]] = None,
        branch_name: Optional[str] = None,
        auto_create_pr: bool = True,
    ) -> Optional[dict[str, Any]]:
        """Generate code using Cursor Cloud Agents.

        Uses agent-based flow: create agent → generate code.

        :param prompt: Code generation prompt/requirements
        :type prompt: str
        :param context: Additional context about the ticket
        :type context: Optional[str]
        :param file_references: list of relevant file paths
        :type file_references: Optional[list[str]]
        :param codebase_context: Codebase context/summary
        :type codebase_context: Optional[str]
        :param file_contents: dictionary mapping file paths to their contents
        :type file_contents: Optional[dict[str, str]]
        :param branch_name: Branch name for target (optional)
        :type branch_name: Optional[str]
        :param auto_create_pr: Whether to auto-create PR (default: True)
        :type auto_create_pr: bool
        :return: dict with 'code' and optionally 'pr' info, or None
        :rtype: Optional[dict[str, Any]]
        """
        logger.info("Generating code using Cursor Cloud Agents")
        agent_id: Optional[str] = None

        try:
            # Step 1: Create agent
            agent_id = self.create_agent(
                prompt=prompt,
                context=context,
                file_references=file_references,
                codebase_context=codebase_context,
                file_contents=file_contents,
                branch_name=branch_name,
                auto_create_pr=auto_create_pr,
            )

            if not agent_id:
                logger.error("Failed to create agent for code generation")
                return None

            logger.info("Created agent %s for code generation", agent_id)

            # Step 2: Get agent status/result (poll until complete)
            result = self._wait_for_agent_completion(
                agent_id, branch_name=branch_name, auto_create_pr=auto_create_pr
            )

            if result:
                logger.info("Successfully generated code using agent %s", agent_id)
                return result

            logger.warning("Failed to generate code from agent %s", agent_id)
            return None

        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Catching general exception is acceptable here for error handling
            logger.error(
                f"Error generating code with Cursor Cloud Agents: {exc}",
                exc_info=True,
            )
            return None

    def create_agent(
        self,
        prompt: str,
        context: Optional[str] = None,
        file_references: Optional[list[str]] = None,
        codebase_context: Optional[str] = None,
        file_contents: Optional[dict[str, str]] = None,
        branch_name: Optional[str] = None,
        auto_create_pr: bool = True,
    ) -> Optional[str]:
        """Create a new agent for code generation.

        :param prompt: Code generation prompt/requirements
        :type prompt: str
        :param context: Additional context about the ticket
        :type context: Optional[str]
        :param file_references: list of relevant file paths
        :type file_references: Optional[list[str]]
        :param codebase_context: Codebase context/summary
        :type codebase_context: Optional[str]
        :param file_contents: dictionary mapping file paths to their contents
        :type file_contents: Optional[dict[str, str]]
        :param branch_name: Branch name for target (optional)
        :type branch_name: Optional[str]
        :param auto_create_pr: Whether to auto-create PR (default: True)
        :type auto_create_pr: bool
        :return: Agent ID or None if creation failed
        :rtype: Optional[str]
        """
        logger.info("Creating agent for code generation")

        # Build the request payload
        payload = self._build_agent_creation_payload(
            prompt=prompt,
            context=context,
            file_references=file_references,
            codebase_context=codebase_context,
            file_contents=file_contents,
            branch_name=branch_name,
            auto_create_pr=auto_create_pr,
        )

        # Call Cursor Cloud Agents API with retry
        response = self._call_api_with_retry(
            method="POST",
            endpoint="v0/agents",
            payload=payload,
        )

        if response:
            agent_id = self._extract_agent_id_from_response(response)
            if agent_id:
                logger.info("Successfully created agent: %s", agent_id)
                return agent_id

        logger.warning("Failed to create agent")
        return None

    def get_agent_status(self, agent_id: str) -> Optional[dict[str, Any]]:
        """Get agent status and result.

        :param agent_id: Agent ID
        :type agent_id: str
        :return: Agent status/result dictionary or None if failed
        :rtype: Optional[dict[str, Any]]
        """
        logger.debug("Getting status for agent %s", agent_id)

        response = self._call_api_with_retry(
            method="GET",
            endpoint=f"v0/agents/{agent_id}",
            payload=None,
        )

        if response:
            return response

        logger.warning("Failed to get status for agent %s", agent_id)
        return None

    def _build_agent_creation_payload(
        self,
        prompt: str,
        context: Optional[str],
        file_references: Optional[list[str]],
        codebase_context: Optional[str],
        file_contents: Optional[dict[str, str]] = None,
        branch_name: Optional[str] = None,
        auto_create_pr: bool = True,
    ) -> dict[str, Any]:
        """Build the API request payload for agent creation.

        Follows the API structure from:
        https://cursor.com/docs/cloud-agent/api/endpoints#launch-an-agent

        :param prompt: Generation prompt
        :type prompt: str
        :param context: Additional context
        :type context: Optional[str]
        :param file_references: File references
        :type file_references: Optional[list[str]]
        :param codebase_context: Codebase context
        :type codebase_context: Optional[str]
        :param file_contents: dictionary mapping file paths to their contents
        :type file_contents: Optional[dict[str, str]]
        :param branch_name: Branch name for target (optional)
        :type branch_name: Optional[str]
        :param auto_create_pr: Whether to auto-create PR (default: True)
        :type auto_create_pr: bool
        :return: Request payload
        :rtype: dict[str, Any]
        """
        # Combine prompt with context and codebase_context into a single prompt
        # text. According to API docs, file references and contents should be
        # included as text context, not as separate keys.
        prompt_parts = [prompt]

        if context:
            prompt_parts.append(f"\n\nContext: {context}")

        if codebase_context:
            prompt_parts.append(f"\n\nCodebase Context: {codebase_context}")

        # Add file references as text context
        if file_references:
            file_refs_text = "\n".join(file_references)
            prompt_parts.append(f"\n\nFile References:\n{file_refs_text}")
            logger.info(
                "Including %d file reference(s) in prompt text",
                len(file_references),
            )

        # Add file contents as text context
        if file_contents:
            file_contents_text = "\n\nFile Contents:\n"
            for file_path, content in file_contents.items():
                file_contents_text += f"\n--- {file_path} ---\n{content}\n"
            prompt_parts.append(file_contents_text)
            logger.info(f"Including {len(file_contents)} file(s) content in prompt text")

        full_prompt_text = "\n".join(prompt_parts)

        # Build prompt object according to API docs
        # https://cursor.com/docs/cloud-agent/api/endpoints#launch-an-agent
        # The prompt object should only contain "text" key
        prompt_obj: dict[str, Any] = {
            "text": full_prompt_text,
        }

        # Build the payload with required fields according to API docs
        payload: dict[str, Any] = {
            "prompt": prompt_obj,
        }

        # Source is required according to API docs
        # https://cursor.com/docs/cloud-agent/api/endpoints#launch-an-agent
        # Repository URL is required
        if not self.repository_url:
            logger.error(
                "Repository URL is required for agent creation. "
                "Please provide repository_url to CursorCloudClient."
            )
            raise ValueError(
                "repository_url is required for agent creation. "
                "The API requires 'source.repository' field."
            )

        payload["source"] = {
            "repository": self.repository_url,
            "ref": self.repository_ref,
        }

        # Add target section if branch_name is provided
        if branch_name:
            payload["target"] = {
                "autoCreatePr": auto_create_pr,
                "branchName": branch_name,
            }
            logger.info(f"Target configured: branch={branch_name}, autoCreatePr={auto_create_pr}")

        # Log the payload for debugging (excluding sensitive data)
        logger.info("Agent creation payload:")
        prompt_preview = full_prompt_text[:500]
        logger.info("  Prompt text (first 500 chars): %s...", prompt_preview)
        logger.info("  Prompt text length: %d chars", len(full_prompt_text))
        logger.info("  Source: %s", payload.get("source"))
        if "target" in payload:
            logger.info("  Target: %s", payload.get("target"))
        file_ref_count = len(file_references) if file_references else 0
        file_content_count = len(file_contents) if file_contents else 0
        logger.info(
            "  File references in prompt: %d, File contents in prompt: %d",
            file_ref_count,
            file_content_count,
        )
        # Log full prompt text for debugging
        logger.info("Full prompt text:\n%s", full_prompt_text)
        # Log payload structure (excluding large file contents)
        payload_for_log = {
            "prompt": {
                "text": f"[{len(full_prompt_text)} chars]",
                "file_references": file_references,
                "file_contents_count": file_content_count,
            },
            "source": payload.get("source"),
        }
        payload_json = json.dumps(payload_for_log, indent=2)
        logger.debug("Payload structure: %s", payload_json)

        return payload

    def _call_api_with_retry(
        self,
        method: str,
        endpoint: str,
        payload: Optional[dict[str, Any]] = None,
        max_retries: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
    ) -> Optional[dict[str, Any]]:
        """Call Cursor Cloud Agents API with exponential backoff retry.

        Implements exponential backoff following Cursor API best practices:
        https://cursor.com/docs/api#1-implement-exponential-backoff

        :param method: HTTP method (GET, POST, DELETE)
        :type method: str
        :param endpoint: API endpoint (relative to base URL)
        :type endpoint: str
        :param payload: Request payload (for POST requests)
        :type payload: Optional[dict[str, Any]]
        :param max_retries: Maximum number of retry attempts
        :type max_retries: int
        :param initial_delay: Initial retry delay in seconds
        :type initial_delay: float
        :param max_delay: Maximum retry delay in seconds
        :type max_delay: float
        :return: API response or None if failed
        :rtype: Optional[dict[str, Any]]
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        delay = initial_delay

        for attempt in range(max_retries + 1):
            try:
                logger.debug(
                    f"Calling Cursor Cloud API: {method} {url} "
                    f"(attempt {attempt + 1}/{max_retries + 1})"
                )

                # Make the API call based on method
                if method.upper() == "GET":
                    response = requests.get(
                        url,
                        headers=self.headers,
                        timeout=300,
                    )
                elif method.upper() == "POST":
                    response = requests.post(
                        url,
                        headers=self.headers,
                        json=payload,
                        timeout=300,
                    )
                elif method.upper() == "DELETE":
                    response = requests.delete(
                        url,
                        headers=self.headers,
                        timeout=300,
                    )
                else:
                    logger.error("Unsupported HTTP method: %s", method)
                    return None

                response.raise_for_status()
                return response.json()

            except Timeout:
                if attempt < max_retries:
                    logger.warning(
                        f"Timeout calling Cursor Cloud API (attempt "
                        f"{attempt + 1}/{max_retries + 1}). "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                else:
                    logger.error(
                        f"Timeout calling Cursor Cloud Agents API after {max_retries + 1} attempts"
                    )
                    return None

            except RequestException as exc:
                # Check if we should retry
                should_retry = False
                retry_after = None

                if hasattr(exc, "response") and exc.response is not None:
                    status_code = exc.response.status_code

                    # Retry on rate limit (429) and service unavailable (503)
                    if status_code == 429:
                        should_retry = True
                        # Check for Retry-After header
                        retry_after_header = exc.response.headers.get("Retry-After")
                        if retry_after_header:
                            try:
                                retry_after = float(retry_after_header)
                            except (ValueError, TypeError):
                                pass
                        logger.warning(
                            f"Rate limited (429) on attempt {attempt + 1}/{max_retries + 1}"
                        )
                    elif status_code == 503:
                        should_retry = True
                        logger.warning(
                            f"Service unavailable (503) on attempt {attempt + 1}/{max_retries + 1}"
                        )
                    # Don't retry on client errors (except 429)
                    elif 400 <= status_code < 500:
                        logger.error(
                            f"Client error ({status_code}) calling "
                            f"Cursor Cloud Agents API: {exc}. "
                            f"Response: {exc.response.text[:500]}"
                        )
                        return None

                # Check for DNS/connection errors (transient, should retry)
                error_msg = str(exc)
                if (
                    "Failed to resolve" in error_msg
                    or "NameResolutionError" in error_msg
                    or "Connection" in error_msg
                ):
                    should_retry = True
                    logger.warning(
                        f"Connection error on attempt {attempt + 1}/{max_retries + 1}: {exc}"
                    )

                if should_retry and attempt < max_retries:
                    # Use Retry-After header if available, otherwise use
                    # exponential backoff
                    wait_time = retry_after if retry_after else delay
                    # Add jitter to prevent thundering herd
                    jittered_delay = wait_time * (0.5 + random.random())
                    # Cap at max_delay
                    jittered_delay = min(jittered_delay, max_delay)

                    logger.info(
                        f"Retrying in {jittered_delay:.2f} seconds "
                        f"(attempt {attempt + 1}/{max_retries + 1})"
                    )
                    time.sleep(jittered_delay)

                    # Exponential backoff: double the delay for next attempt
                    delay = min(delay * 2, max_delay)
                else:
                    # Final attempt failed or non-retryable error
                    if hasattr(exc, "response") and exc.response is not None:
                        logger.error(
                            "Error calling Cursor Cloud Agents API: %s. Response: %s",
                            exc,
                            exc.response.text[:500],
                        )
                    else:
                        logger.error("Error calling Cursor Cloud Agents API: %s", exc)
                    return None

            except Exception as exc:  # pylint: disable=broad-exception-caught
                # Catching general exception is acceptable here for error
                # handling
                error_msg = str(exc)
                if "Failed to resolve" in error_msg or "NameResolutionError" in error_msg:
                    logger.error(
                        "DNS resolution error for Cursor Cloud API "
                        "(%s). Please verify the API endpoint "
                        "is correct. Error: %s",
                        self.base_url,
                        exc,
                    )
                else:
                    logger.error("Unexpected error calling Cursor Cloud API: %s", exc)
                return None

        return None

    def _extract_agent_id_from_response(self, response: dict[str, Any]) -> Optional[str]:
        """Extract agent ID from agent creation response.

        :param response: API response dictionary
        :type response: dict[str, Any]
        :return: Agent ID or None
        :rtype: Optional[str]
        """
        # Try different response formats for agent ID
        if "id" in response:
            return str(response["id"])

        if "agent_id" in response:
            return str(response["agent_id"])

        if "agent" in response and isinstance(response["agent"], dict):
            agent = response["agent"]
            if "id" in agent:
                return str(agent["id"])

        logger.warning(f"Could not extract agent ID from response: {json.dumps(response)[:200]}")
        return None

    def _wait_for_agent_completion(
        self,
        agent_id: str,
        max_wait_time: int = 600,
        poll_interval: int = 5,
        branch_name: Optional[str] = None,
        auto_create_pr: bool = False,
    ) -> Optional[dict[str, Any]]:
        """Wait for agent to complete and return generated code.

        According to Cursor Cloud Agent API documentation:
        https://cursor.com/docs/cloud-agent/api/endpoints#agent-status
        Status values: FINISHED, ERROR, RUNNING

        :param agent_id: Agent ID
        :type agent_id: str
        :param max_wait_time: Maximum time to wait in seconds (default: 600)
        :type max_wait_time: int
        :param poll_interval: Interval between status checks in seconds
            (default: 5)
        :type poll_interval: int
        :param branch_name: Branch name (for PR lookup if auto_create_pr=True)
        :type branch_name: Optional[str]
        :param auto_create_pr: Whether PR was auto-created (for PR extraction)
        :type auto_create_pr: bool
        :return: dictionary with 'code' and optionally 'pr' info, or None
        :rtype: Optional[dict[str, Any]]
        """
        logger.info(
            f"Waiting for agent {agent_id} to complete "
            f"(max wait: {max_wait_time}s, poll interval: {poll_interval}s)"
        )

        start_time = time.time()
        consecutive_failures = 0
        max_consecutive_failures = 5  # Exit after 5 consecutive failures

        while time.time() - start_time < max_wait_time:
            status_response = self.get_agent_status(agent_id)

            if not status_response:
                consecutive_failures += 1
                logger.warning(
                    "Failed to get status for agent %s (consecutive failures: %d/%d)",
                    agent_id,
                    consecutive_failures,
                    max_consecutive_failures,
                )

                # Exit if too many consecutive failures
                if consecutive_failures >= max_consecutive_failures:
                    logger.error(
                        "Too many consecutive API failures (%d). "
                        "Agent %s may have completed but status check "
                        "is failing. Exiting to avoid indefinite polling.",
                        consecutive_failures,
                        agent_id,
                    )
                    return None

                # Exponential backoff for failures
                backoff_time = min(poll_interval * (2 ** (consecutive_failures - 1)), 30)
                time.sleep(backoff_time)
                continue

            # Reset consecutive failures counter on successful status check
            consecutive_failures = 0

            # Check if agent is complete using API documentation status values
            # Status values: FINISHED, ERROR, RUNNING (case-insensitive)
            status = status_response.get("status", "").upper()
            state = status_response.get("state", "").upper()

            # Check for FINISHED status (per API docs)
            if status == "FINISHED" or state == "FINISHED":
                logger.info("Agent %s status: FINISHED", agent_id)

                # Log full response for debugging
                logger.debug(
                    "Agent %s FINISHED response: %s",
                    agent_id,
                    json.dumps(status_response, indent=2)[:1000],
                )

                # Extract PR URL from agent status response
                pr_url = None
                if "target" in status_response:
                    target = status_response.get("target")
                    if isinstance(target, dict):
                        pr_url = target.get("prUrl") or target.get("pr_url")

                # Agent completed successfully - PR was created by Cursor
                result = {"status": "finished"}
                if pr_url:
                    result["pr_url"] = pr_url
                    logger.info(
                        "Agent %s status is FINISHED. PR was created by Cursor Cloud Agents: %s",
                        agent_id,
                        pr_url,
                    )
                else:
                    logger.info(
                        "Agent %s status is FINISHED. PR was created by Cursor Cloud Agents.",
                        agent_id,
                    )
                return result

            # Check for EXPIRED status (agent has expired/completed)
            if status == "EXPIRED" or state == "EXPIRED":
                logger.info("Agent %s status: EXPIRED", agent_id)

                # Log full response for debugging
                logger.debug(
                    "Agent %s EXPIRED response: %s",
                    agent_id,
                    json.dumps(status_response, indent=2)[:1000],
                )

                # Extract PR URL from agent status response
                pr_url = None
                if "target" in status_response:
                    target = status_response.get("target")
                    if isinstance(target, dict):
                        pr_url = target.get("prUrl") or target.get("pr_url")

                # Agent completed successfully - PR was created by Cursor
                result = {"status": "expired"}
                if pr_url:
                    result["pr_url"] = pr_url
                    logger.info(
                        "Agent %s status is EXPIRED. PR was created by Cursor Cloud Agents: %s",
                        agent_id,
                        pr_url,
                    )
                else:
                    logger.info(
                        "Agent %s status is EXPIRED. PR was created by Cursor Cloud Agents.",
                        agent_id,
                    )
                return result

            # Check for ERROR status (per API docs)
            if status == "ERROR" or state == "ERROR":
                error_msg = status_response.get("error", "Unknown error")
                logger.error("Agent %s status: ERROR - %s", agent_id, error_msg)
                return None

            # Check for RUNNING status (per API docs)
            if status == "RUNNING" or state == "RUNNING":
                logger.debug(
                    "Agent %s status: RUNNING, waiting %ds before next check",
                    agent_id,
                    poll_interval,
                )
                time.sleep(poll_interval)
                continue

            # Handle legacy status values for backward compatibility
            status_lower = status.lower()
            state_lower = state.lower()

            if status_lower in (
                "completed",
                "done",
                "success",
            ) or state_lower in (
                "completed",
                "done",
                "success",
            ):
                # Extract PR URL from agent status response
                pr_url = None
                if "target" in status_response:
                    target = status_response.get("target")
                    if isinstance(target, dict):
                        pr_url = target.get("prUrl") or target.get("pr_url")

                result = {"status": "finished"}
                if pr_url:
                    result["pr_url"] = pr_url
                    logger.info(
                        "Agent %s completed (legacy status format: %s). "
                        "PR was created by Cursor Cloud Agents: %s",
                        agent_id,
                        status or state,
                        pr_url,
                    )
                else:
                    logger.info(
                        "Agent %s completed (legacy status format: %s). "
                        "PR was created by Cursor Cloud Agents.",
                        agent_id,
                        status or state,
                    )
                return result

            if status_lower in ("failed", "error") or state_lower in (
                "failed",
                "error",
            ):
                error_msg = status_response.get("error", "Unknown error")
                logger.error("Agent %s failed: %s", agent_id, error_msg)
                return None

            # Unknown status - log and continue polling
            logger.debug(
                "Agent %s status: %s, waiting %ds before next check",
                agent_id,
                status or state or "unknown",
                poll_interval,
            )
            time.sleep(poll_interval)

        logger.error(
            "Timeout waiting for agent %s to complete (waited %ds)",
            agent_id,
            max_wait_time,
        )
        return None
