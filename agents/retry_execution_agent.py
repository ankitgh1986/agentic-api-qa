import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class RetryExecutionAgent:
    """
    Executes an operation with retry semantics.

    This agent is independent from validation, reporting and retry decision logic.
    It simply re-invokes the provided execution agent according to the
    provided retry decision.
    """

    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 1

    def execute_with_retry(
        self,
        operation: Dict[str, Any],
        payload: Optional[Dict[str, Any]],
        execution_agent: Any,
        retry_decision: Dict[str, Any],
        initial_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute the given operation and optionally retry it according to
        `retry_decision`.

        Args:
            operation: Operation metadata.
            payload: Optional request payload to pass to the executor.
            execution_agent: An object exposing `execute_operation(operation, payload)`.
            retry_decision: Result from `RetryDecisionAgent.should_retry()` indicating
                            whether to retry and why.

        Returns:
            Final execution result dictionary augmented with retry metadata:
            - `retried`: bool (True when at least one retry attempt was made)
            - `retry_attempts`: int (number of retry attempts performed)
            - `retry_successful`: bool (True when a retry produced success)
        """
        # Validate retry decision shape
        if not isinstance(retry_decision, dict):
            logger.info("Invalid retry_decision provided; skipping retries.")
            retry_decision = {"retry": False, "reason": "invalid_decision"}

        should_retry = bool(retry_decision.get("retry", False))

        # Use provided initial result as the starting point
        if not isinstance(initial_result, dict):
            logger.info("Invalid initial_result provided; creating failure-shaped initial result.")
            result = {
                "method": operation.get("method"),
                "path": operation.get("path"),
                "status_code": None,
                "response_time_ms": None,
                "success": False,
                "response_body": None,
                "error": "invalid_initial_result",
                "execution_status": "Failed",
                "skip_reason": "",
            }
        else:
            result = dict(initial_result)

        # If not requested to retry, return the initial result unchanged (with metadata)
        if not should_retry or result.get("success", False):
            result["retried"] = False
            result["retry_attempts"] = 0
            result["retry_successful"] = bool(result.get("success", False))
            logger.info("RetryExecutionAgent: retries not requested or initial result succeeded; returning initial result.")
            return result

        # Retry loop: only invoke execution_agent when performing actual retry attempts
        attempts = 0
        retry_successful = False

        while attempts < self.MAX_RETRIES and not retry_successful:
            attempts += 1
            logger.info(
                "RetryExecutionAgent: attempt %s/%s for %s %s",
                attempts,
                self.MAX_RETRIES,
                operation.get("method"),
                operation.get("path"),
            )
            try:
                time.sleep(self.RETRY_DELAY_SECONDS)
                attempt_result = execution_agent.execute_operation(
                    operation=operation,
                    payload=payload,
                )

                # Update result with attempt outcome
                result = attempt_result
                retry_successful = bool(result.get("success", False))

                if retry_successful:
                    logger.info(
                        "RetryExecutionAgent: retry successful on attempt %s for %s %s",
                        attempts,
                        operation.get("method"),
                        operation.get("path"),
                    )
                    break

                logger.info(
                    "RetryExecutionAgent: retry attempt %s did not succeed for %s %s",
                    attempts,
                    operation.get("method"),
                    operation.get("path"),
                )

            except Exception as exc:
                logger.exception(
                    "RetryExecutionAgent: exception during retry attempt %s for %s %s: %s",
                    attempts,
                    operation.get("method"),
                    operation.get("path"),
                    exc,
                )
                # Create a failure-shaped result to preserve flow
                result = {
                    "method": operation.get("method"),
                    "path": operation.get("path"),
                    "status_code": None,
                    "response_time_ms": None,
                    "success": False,
                    "response_body": None,
                    "error": str(exc),
                    "execution_status": "Failed",
                    "skip_reason": "",
                }

        # Final metadata
        result["retried"] = attempts > 0
        result["retry_attempts"] = attempts
        result["retry_successful"] = retry_successful

        if retry_successful:
            logger.info(
                "RetryExecutionAgent: operation %s %s succeeded after %s attempt(s)",
                operation.get("method"),
                operation.get("path"),
                attempts,
            )
        else:
            logger.info(
                "RetryExecutionAgent: operation %s %s failed after %s attempt(s)",
                operation.get("method"),
                operation.get("path"),
                attempts,
            )

        return result
