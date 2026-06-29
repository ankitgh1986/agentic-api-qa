import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class RetryDecisionAgent:
    """
    Decides whether a failed API execution should be retried.

    This agent inspects the execution result and returns a simple retry
    decision without executing retries itself.
    """

    TIMEOUT_INDICATORS = [
        "timeout",
        "timed out",
        "read timeout",
        "connect timeout",
        "connection timed out",
    ]

    CONNECTION_INDICATORS = [
        "connection",
        "connection aborted",
        "connection reset",
        "connection refused",
        "connection error",
        "name or service not known",
        "network is unreachable",
        "temporary failure in name resolution",
    ]

    def should_retry(
        self,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Determine whether the request should be retried.

        Args:
            result: Execution result dictionary containing status and error data.

        Returns:
            Dictionary containing:
                - retry: bool
                - reason: str
                - category: str
        """
        if not isinstance(result, dict):
            retry = False
            reason = "Invalid result object; cannot determine retry policy."
            category = "INVALID_RESULT"
            logger.info("Retry decision: %s (%s) category=%s", retry, reason, category)
            return {"retry": retry, "reason": reason, "category": category}

        status_code = result.get("status_code")
        error = result.get("error")
        error_text = str(error or "").strip().lower()

        if result.get("success"):
            retry = False
            reason = "Request succeeded; no retry needed."
            category = "SUCCESS"
            logger.info("Retry decision: %s (%s) category=%s", retry, reason, category)
            return {"retry": retry, "reason": reason, "category": category}

        if status_code in {500, 502, 503, 504}:
            retry = True
            reason = f"Retryable server error: HTTP {status_code}."
            category = "SERVER_ERROR"
            logger.info("Retry decision: %s (%s) category=%s", retry, reason, category)
            return {"retry": retry, "reason": reason, "category": category}

        if status_code in {400, 401, 403, 404, 422}:
            retry = False
            reason = f"Client error: HTTP {status_code}; do not retry."
            category = "CLIENT_ERROR"
            logger.info("Retry decision: %s (%s) category=%s", retry, reason, category)
            return {"retry": retry, "reason": reason, "category": category}

        if any(token in error_text for token in self.TIMEOUT_INDICATORS):
            retry = True
            reason = "Timeout-related error detected; retry recommended."
            category = "TIMEOUT"
            logger.info("Retry decision: %s (%s) category=%s", retry, reason, category)
            return {"retry": retry, "reason": reason, "category": category}

        if any(token in error_text for token in self.CONNECTION_INDICATORS):
            retry = True
            reason = "Connection-related error detected; retry recommended."
            category = "CONNECTION_ERROR"
            logger.info("Retry decision: %s (%s) category=%s", retry, reason, category)
            return {"retry": retry, "reason": reason, "category": category}

        retry = False
        reason = "No retry conditions met."
        category = "UNKNOWN"
        logger.info("Retry decision: %s (%s) category=%s", retry, reason, category)
        return {"retry": retry, "reason": reason, "category": category}
