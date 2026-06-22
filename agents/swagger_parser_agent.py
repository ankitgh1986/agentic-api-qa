import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)

VALID_HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"}


class SwaggerParserError(Exception):
    """Base exception for SwaggerParserAgent errors."""


class OpenAPIValidationError(SwaggerParserError):
    """Raised when the OpenAPI structure is malformed."""


class SwaggerParserAgent:
    """Parser for Swagger/OpenAPI JSON documents.

    The agent reads a Swagger/OpenAPI JSON file, validates its structure,
    and extracts API endpoint paths and HTTP methods.
    """

    def __init__(self, spec_path: Union[str, Path]) -> None:
        """Initialize the parser with the OpenAPI file path.

        Args:
            spec_path: Path to a Swagger/OpenAPI JSON file.

        Raises:
            FileNotFoundError: If the JSON file does not exist.
            json.JSONDecodeError: If the file contains invalid JSON.
            OpenAPIValidationError: If the OpenAPI structure is malformed.
        """
        self.spec_path = Path(spec_path)
        self._spec: Dict[str, Any] = {}
        self._paths: Dict[str, Any] = {}
        self._extracted_paths: List[Dict[str, Any]] = []

        logger.debug("Initializing SwaggerParserAgent with path: %s", self.spec_path)
        self._load_spec()
        self._validate_spec()
        self._extract_operations()

    def _load_spec(self) -> None:
        """Load and parse the JSON OpenAPI specification from disk."""
        if not self.spec_path.exists():
            logger.error("Swagger/OpenAPI file not found: %s", self.spec_path)
            raise FileNotFoundError(f"Swagger/OpenAPI file not found: {self.spec_path}")

        try:
            with self.spec_path.open("r", encoding="utf-8") as file:
                self._spec = json.load(file)
                logger.debug("Swagger/OpenAPI file loaded successfully")
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in Swagger/OpenAPI file: %s", exc)
            raise

    def _validate_spec(self) -> None:
        """Validate the loaded OpenAPI structure for required fields."""
        if not isinstance(self._spec, dict):
            logger.error("OpenAPI document is not a JSON object")
            raise OpenAPIValidationError("OpenAPI document must be a JSON object.")

        paths = self._spec.get("paths")
        if paths is None:
            logger.error("Missing 'paths' section in OpenAPI document")
            raise OpenAPIValidationError("OpenAPI document is missing the 'paths' section.")

        if not isinstance(paths, dict):
            logger.error("OpenAPI 'paths' section is malformed: expected object, got %s", type(paths).__name__)
            raise OpenAPIValidationError("OpenAPI 'paths' section must be an object mapping paths to operations.")

        logger.debug("OpenAPI 'paths' section validated successfully")
        self._paths = paths

    def _extract_operations(self) -> None:
        """Extract API operations and metadata from the OpenAPI specification."""
        logger.debug("Extracting API operations from OpenAPI document")
        extracted: List[Dict[str, Any]] = []

        for path, methods in self._paths.items():
            if not isinstance(methods, dict):
                logger.warning("Skipping malformed path entry '%s'; expected object of methods.", path)
                continue

            for method, operation in methods.items():
                normalized_method = method.strip().upper()
                if normalized_method not in VALID_HTTP_METHODS:
                    logger.debug("Ignoring non-HTTP method key '%s' for path '%s'", method, path)
                    continue

                if not isinstance(operation, dict):
                    logger.warning("Skipping malformed operation for %s %s; expected object.", normalized_method, path)
                    continue

                summary = operation.get("summary", "")
                description = operation.get("description", "")
                tags = operation.get("tags", [])
                operation_id = operation.get("operationId", "")
                responses = operation.get("responses", {})

                if not isinstance(tags, list):
                    logger.warning("Expected tags to be a list for %s %s; coercing to empty list.", normalized_method, path)
                    tags = []

                if not isinstance(responses, dict):
                    logger.warning("Expected responses to be a dict for %s %s; coercing to empty dict.", normalized_method, path)
                    responses = {}

                response_codes = [str(code) for code in responses.keys()]

                extracted_operation = {
                    "method": normalized_method,
                    "path": path,
                    "summary": summary,
                    "description": description,
                    "tags": tags,
                    "operation_id": operation_id,
                    "response_codes": response_codes,
                }

                extracted.append(extracted_operation)
                logger.debug(
                    "Extracted API operation: %s %s summary=%s operation_id=%s responses=%s",
                    normalized_method,
                    path,
                    summary,
                    operation_id,
                    response_codes,
                )

        self._extracted_paths = extracted
        logger.info("Extracted %d API operations from OpenAPI document", len(extracted))

    def get_operations(self) -> List[Dict[str, Any]]:
        """Return the list of extracted API operations.

        Returns:
            A list of dictionaries, each containing operation metadata.
        """
        return list(self._extracted_paths)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(spec_path={self.spec_path!r}, operations={len(self._extracted_paths)})"
