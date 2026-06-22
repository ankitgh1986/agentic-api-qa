import logging
import re
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class ScenarioGenerationError(Exception):
    """Base exception for ScenarioGenerationAgent errors."""


class ScenarioGenerationAgent:
    """Generate test scenarios from Swagger/OpenAPI operations."""

    def __init__(self, operations: List[Dict[str, Any]]) -> None:
        """Initialize the scenario generator with parsed API operations.

        Args:
            operations: A list of operation metadata dictionaries.

        Raises:
            ScenarioGenerationError: If the operations input is invalid.
        """
        self._operations = operations
        self._scenarios: List[Dict[str, Any]] = []

        logger.debug("Initializing ScenarioGenerationAgent with %d operations", len(operations))
        self._validate_operations()

    def _validate_operations(self) -> None:
        """Validate the input operations list structure."""
        if not isinstance(self._operations, list):
            logger.error("Operations input must be a list")
            raise ScenarioGenerationError("Operations input must be a list of dictionaries.")

        for index, operation in enumerate(self._operations):
            if not isinstance(operation, dict):
                logger.error("Operation at index %d is not a dictionary", index)
                raise ScenarioGenerationError("Each operation must be a dictionary.")

            missing_keys = [key for key in ("method", "path", "response_codes") if key not in operation]
            if missing_keys:
                logger.error("Operation at index %d is missing keys: %s", index, missing_keys)
                raise ScenarioGenerationError(f"Operation is missing required keys: {missing_keys}")

            if not isinstance(operation.get("method"), str):
                logger.error("Operation method at index %d is not a string", index)
                raise ScenarioGenerationError("Operation 'method' must be a string.")

            if not isinstance(operation.get("path"), str):
                logger.error("Operation path at index %d is not a string", index)
                raise ScenarioGenerationError("Operation 'path' must be a string.")

            response_codes = operation.get("response_codes")
            if not isinstance(response_codes, list):
                logger.error("Operation response_codes at index %d is not a list", index)
                raise ScenarioGenerationError("Operation 'response_codes' must be a list of strings.")

        logger.debug("Validated %d operations successfully", len(self._operations))

    def generate_scenarios(self) -> List[Dict[str, Any]]:
        """Generate scenario definitions for the configured operations.

        Returns:
            A list of scenario dictionaries for each API operation.
        """
        if self._scenarios:
            logger.debug("Returning previously generated scenarios")
            return list(self._scenarios)

        for operation in self._operations:
            scenario_definition = self._build_scenario_definition(operation)
            self._scenarios.append(scenario_definition)
            logger.debug(
                "Generated %d scenarios for %s %s",
                len(scenario_definition["scenarios"]),
                operation["method"],
                operation["path"],
            )

        logger.info("Generated scenarios for %d API operations", len(self._scenarios))
        return list(self._scenarios)

    def _build_scenario_definition(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Build a scenario definition for a single API operation."""
        method = str(operation["method"]).upper()
        path = str(operation["path"])
        summary = self._get_text_value(operation.get("summary"))
        response_codes = self._normalize_response_codes(operation.get("response_codes"))

        base_scenarios = self._base_scenarios_for_method(method, path, summary)
        parameter_scenarios = self._parameter_scenarios(path)
        response_scenarios = self._scenarios_from_response_codes(response_codes, path, method)
        all_base_scenarios = base_scenarios + parameter_scenarios
        positive_scenarios, negative_scenarios = self._categorize_base_scenarios(all_base_scenarios)

        return {
            "api": path,
            "method": method,
            "scenarios": all_base_scenarios + response_scenarios,
            "positive_scenarios": positive_scenarios,
            "negative_scenarios": negative_scenarios,
            "validation_scenarios": response_scenarios,
        }

    def _base_scenarios_for_method(self, method: str, path: str, summary: str) -> List[str]:
        """Return base positive and negative scenarios for a given HTTP method."""
        if method == "GET":
            return [
                self._positive_scenario(method, path, summary),
                f"Verify invalid path parameter handling for {path}.",
                f"Verify null parameter handling for {path}.",
                f"Verify resource-not-found behavior for {path}.",
                f"Verify unauthorized access handling for {path}.",
            ]

        if method == "POST":
            return [
                self._positive_scenario(method, path, summary),
                f"Verify missing mandatory field handling for {path}.",
                f"Verify invalid field value handling for {path}.",
                f"Verify empty payload handling for {path}.",
                f"Verify duplicate request handling for {path}.",
            ]

        if method == "PUT":
            return [
                self._positive_scenario(method, path, summary),
                f"Verify update of non-existent resource for {path}.",
                f"Verify invalid payload handling for {path}.",
                f"Verify missing mandatory fields for {path}.",
            ]

        if method == "DELETE":
            return [
                self._positive_scenario(method, path, summary),
                f"Verify delete non-existent resource handling for {path}.",
                f"Verify invalid identifier handling for {path}.",
            ]

        if method in {"PATCH", "OPTIONS", "HEAD"}:
            return [
                self._positive_scenario(method, path, summary),
                f"Verify invalid request handling for {path}.",
                f"Verify unauthorized access handling for {path}.",
            ]

        logger.warning("Unsupported HTTP method '%s' for path '%s'", method, path)
        return [self._positive_scenario(method, path, summary)]

    def _positive_scenario(self, method: str, path: str, summary: str) -> str:
        """Build a positive test scenario description."""
        if summary:
            return f"Verify successful {method} request for {path}: {summary}."
        return f"Verify successful {method} request for {path}."

    def _parameter_scenarios(self, path: str) -> List[str]:
        """Generate parameter-aware scenarios from a path with path parameters."""
        parameter_names = self._extract_path_parameters(path)
        scenarios: List[str] = []

        for parameter in parameter_names:
            if self._is_identifier_parameter(parameter):
                scenarios.extend([
                    f"Verify valid {parameter} handling for {path}.",
                    f"Verify invalid {parameter} handling for {path}.",
                    f"Verify negative {parameter} handling for {path}.",
                    f"Verify null {parameter} handling for {path}.",
                    f"Verify very large {parameter} handling for {path}.",
                ])
            else:
                scenarios.extend([
                    f"Verify valid {parameter} handling for {path}.",
                    f"Verify empty {parameter} handling for {path}.",
                    f"Verify special character {parameter} handling for {path}.",
                    f"Verify non-existent {parameter} handling for {path}.",
                ])

        return scenarios

    def _extract_path_parameters(self, path: str) -> List[str]:
        """Extract parameter names from a path template."""
        return re.findall(r"\{([^/{}]+)\}", path)

    def _is_identifier_parameter(self, parameter_name: str) -> bool:
        """Return whether a path parameter is likely an identifier."""
        normalized = parameter_name.lower()
        return normalized.endswith("id") or "id" in normalized

    def _categorize_base_scenarios(self, base_scenarios: List[str]) -> Tuple[List[str], List[str]]:
        """Categorize base scenarios into positive and negative groups."""
        positive_scenarios = [scenario for scenario in base_scenarios if scenario.lower().startswith("verify successful")]
        negative_scenarios = [scenario for scenario in base_scenarios if not scenario.lower().startswith("verify successful")]
        return positive_scenarios, negative_scenarios

    def _scenarios_from_response_codes(
        self,
        response_codes: List[str],
        path: str,
        method: str,
    ) -> List[str]:
        """Generate validation scenarios from response status codes."""
        scenario_map = {
            "400": f"Verify bad request handling for {method} {path}.",
            "401": f"Verify unauthorized handling for {method} {path}.",
            "403": f"Verify forbidden handling for {method} {path}.",
            "404": f"Verify resource not found handling for {method} {path}.",
            "409": f"Verify conflict handling for {method} {path}.",
            "422": f"Verify validation error handling for {method} {path}.",
            "500": f"Verify server error handling for {method} {path}.",
        }
        scenarios: List[str] = []

        for code in response_codes:
            mapped = scenario_map.get(code)
            if mapped:
                scenarios.append(mapped)
                continue

            if code.startswith("2"):
                continue

            scenarios.append(f"Verify handling of HTTP {code} for {method} {path}.")

        return scenarios

    def _normalize_response_codes(self, codes: Any) -> List[str]:
        """Normalize response codes into a list of strings."""
        if not isinstance(codes, list):
            logger.warning("Response codes value is not a list; defaulting to empty list")
            return []

        normalized: List[str] = []
        for code in codes:
            if code is None:
                continue
            normalized.append(str(code).strip())

        return [code for code in normalized if code]

    def _get_text_value(self, value: Any) -> str:
        """Return a normalized string value for description or summary fields."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()
