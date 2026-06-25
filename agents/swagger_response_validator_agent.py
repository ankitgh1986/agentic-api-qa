import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SwaggerResponseValidatorAgent:
    """
    Validates API responses against
    documented Swagger response codes.
    """

    def validate(
        self,
        operation: Dict[str, Any],
        execution_result: Dict[str, Any],
    ) -> Dict[str, Any]:

        expected_codes = operation.get(
            "response_codes",
            [],
        )

        actual_code = str(
            execution_result.get(
                "status_code"
            )
        )

        passed = (
            actual_code in expected_codes
        )

        validations = [
            {
                "check": "Swagger Status Validation",
                "passed": passed,
                "expected": expected_codes,
                "actual": actual_code,
            }
        ]

        logger.info(
            "Swagger validation completed. Result=%s",
            "PASS" if passed else "FAIL",
        )

        return {
            "passed": passed,
            "validations": validations,
        }