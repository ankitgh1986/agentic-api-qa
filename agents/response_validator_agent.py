import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ResponseValidatorError(Exception):
    """Base exception for ResponseValidatorAgent."""


class ResponseValidatorAgent:
    """
    Validates API execution results.
    """

    def validate(
        self,
        execution_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate API response.

        Args:
            execution_result: Result returned by ExecutionAgent

        Returns:
            Validation result dictionary.
        """

        status_code = execution_result.get(
            "status_code"
        )

        response_body = execution_result.get(
            "response_body"
        )

        validations = []

        # Status Code Validation
        status_valid = (
            status_code is not None
            and 200 <= status_code < 300
        )

        validations.append(
            {
                "check": "Status Code",
                "passed": status_valid,
            }
        )

        # Response Body Validation
        body_valid = response_body is not None

        validations.append(
            {
                "check": "Response Body Present",
                "passed": body_valid,
            }
        )

        overall_pass = all(
            item["passed"]
            for item in validations
        )

        result = {
            "passed": overall_pass,
            "validations": validations,
        }

        logger.info(
            "Validation completed. Result=%s",
            "PASS" if overall_pass else "FAIL",
        )

        return result