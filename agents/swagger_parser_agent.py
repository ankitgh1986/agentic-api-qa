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

    This class reads a Swagger/OpenAPI JSON file, validates its structure,
    and extracts all paths and supported HTTP methods.
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
        self._operations: List[Dict[str, str]] = []

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
            with self.spec_path.open("r", encoding="utf-8") as spec_file:
                self._spec = json.load(spec_file)
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
            logger.error(
                "OpenAPI 'paths' section is malformed: expected object, got %s",
                type(paths).__name__,
            )
            raise OpenAPIValidationError(
                "OpenAPI 'paths' section must be an object mapping paths to operations."
            )

        logger.debug("OpenAPI 'paths' section validated successfully")
        self._paths = paths

    def _extract_operations(self) -> None:
        """Extract API paths and operation metadata from the OpenAPI structure."""
        logger.debug("Extracting API operations from OpenAPI document")
        operations: List[Dict[str, Any]] = []

        for path, path_item in self._paths.items():
            if not isinstance(path_item, dict):
                logger.warning(
                    "Skipping malformed path entry '%s'; expected object, got %s",
                    path,
                    type(path_item).__name__,
                )
                continue

            for method_name, operation in path_item.items():
                normalized_method = method_name.strip().upper()
                if normalized_method not in VALID_HTTP_METHODS:
                    logger.debug(
                        "Ignoring unsupported path key '%s' for path '%s'",
                        method_name,
                        path,
                    )
                    continue

                if not isinstance(operation, dict):
                    logger.warning(
                        "Skipping malformed operation for %s %s; expected object, got %s",
                        normalized_method,
                        path,
                        type(operation).__name__,
                    )
                    continue

                summary = self._get_text_value(operation.get("summary", ""))
                description = self._get_text_value(operation.get("description", ""))
                tags = operation.get("tags", [])
                if not isinstance(tags, list):
                    logger.warning(
                        "Expected tags to be a list for %s %s; coercing to empty list.",
                        normalized_method,
                        path,
                    )
                    tags = []

                operation_id = self._get_text_value(operation.get("operationId", ""))
                responses = operation.get("responses", {})
                if not isinstance(responses, dict):
                    logger.warning(
                        "Expected responses to be a dict for %s %s; coercing to empty dict.",
                        normalized_method,
                        path,
                    )
                    responses = {}

                response_codes = [str(code) for code in responses.keys()]
                parameters = self._extract_parameters(operation)
                (
                    request_body_required,
                    request_body_content_types,
                    request_schema_ref,
                ) = self._extract_request_body_metadata(operation)

                operations.append(
                    {
                        "method": normalized_method,
                        "path": path,
                        "summary": summary,
                        "description": description,
                        "tags": tags,
                        "operation_id": operation_id,
                        "response_codes": response_codes,
                        "parameters": parameters,
                        "request_body_required": request_body_required,
                        "request_body_content_types": request_body_content_types,
                        "request_schema_ref": request_schema_ref,
                    }
                )
                logger.debug(
                    "Extracted API operation: %s %s summary=%s operation_id=%s responses=%s",
                    normalized_method,
                    path,
                    summary,
                    operation_id,
                    response_codes,
                )

        self._operations = operations
        logger.info("Extracted %d API operations from OpenAPI document", len(operations))

    def _extract_parameters(self, operation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract parameter metadata from an OpenAPI operation."""
        raw_parameters = operation.get("parameters", [])
        if not isinstance(raw_parameters, list):
            logger.warning(
                "Expected parameters to be a list for operation %s %s; coercing to empty list.",
                operation.get("method", ""),
                operation.get("path", ""),
            )
            return []

        parameters: List[Dict[str, Any]] = []
        for parameter in raw_parameters:
            if not isinstance(parameter, dict):
                logger.warning("Skipping malformed parameter entry; expected object, got %s", type(parameter).__name__)
                continue

            schema = parameter.get("schema", {})
            schema_type = ""
            if isinstance(schema, dict):
                type_value = schema.get("type")
                if isinstance(type_value, str):
                    schema_type = type_value
                elif isinstance(type_value, (list, tuple)):
                    schema_type = ",".join(str(item) for item in type_value if item is not None)

            parameters.append(
                {
                    "name": self._get_text_value(parameter.get("name", "")),
                    "in": self._get_text_value(parameter.get("in", "")),
                    "required": bool(parameter.get("required", False)),
                    "type": schema_type,
                }
            )

        return parameters

    def _extract_request_body_metadata(
        self,
        operation: Dict[str, Any],
    ) -> tuple[bool, List[str], Union[str, None]]:
        """Extract request body metadata and schema references from an operation."""
        request_body = operation.get("requestBody")
        if not isinstance(request_body, dict):
            return False, [], None

        required = bool(request_body.get("required", False))
        content = request_body.get("content", {})
        if not isinstance(content, dict):
            logger.warning(
                "Expected requestBody.content to be a dict for operation %s %s; coercing to empty object.",
                operation.get("method", ""),
                operation.get("path", ""),
            )
            return required, [], None

        content_types: List[str] = []
        request_schema_ref: Union[str, None] = None

        for media_type, media_definition in content.items():
            if not isinstance(media_definition, dict):
                logger.warning(
                    "Skipping malformed requestBody media type %s for operation %s %s.",
                    media_type,
                    operation.get("method", ""),
                    operation.get("path", ""),
                )
                continue

            content_types.append(media_type)
            schema = media_definition.get("schema")
            candidate_ref = self._extract_schema_ref(schema)
            if candidate_ref and request_schema_ref is None:
                request_schema_ref = candidate_ref

        return required, content_types, request_schema_ref

    def _extract_schema_ref(self, schema: Any) -> Union[str, None]:
        """Recursively extract a $ref value from a schema object."""
        if not isinstance(schema, dict):
            return None

        ref_value = schema.get("$ref")
        if isinstance(ref_value, str):
            return ref_value

        for composite_key in ("allOf", "oneOf", "anyOf"):
            composite = schema.get(composite_key)
            if isinstance(composite, list):
                for item in composite:
                    candidate_ref = self._extract_schema_ref(item)
                    if candidate_ref:
                        return candidate_ref

        return None
    
    def _get_text_value(self, value: Any) -> str:
        """Return a normalized string value."""
        if value is None:
            return ""

        if isinstance(value, str):
            return value.strip()

        return str(value).strip()

    def get_operations(self) -> List[Dict[str, Any]]:
        """Return the list of extracted API operations.

        Returns:
            A list of dictionaries containing metadata for each operation.
        """
        return list(self._operations)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(spec_path={self.spec_path!r}, "
            f"operations={len(self._operations)})"
        )
