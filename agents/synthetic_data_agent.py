import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SyntheticDataError(Exception):
    """Base exception for SyntheticDataAgent errors."""


class SyntheticDataAgent:
    """Generate synthetic API request payloads from OpenAPI schema definitions."""

    def __init__(
        self,
        schema_name: str,
        schema_definition: Dict[str, Any],
    ) -> None:

        if not isinstance(schema_name, str) or not schema_name.strip():
            logger.error(
                "Invalid schema_name provided: %r",
                schema_name,
            )
            raise SyntheticDataError(
                "schema_name must be a non-empty string."
            )

        if not isinstance(schema_definition, dict):
            logger.error(
                "Invalid schema_definition provided for %s: %r",
                schema_name,
                schema_definition,
            )
            raise SyntheticDataError(
                "schema_definition must be a dictionary."
            )

        self.schema_name = schema_name.strip()
        self.schema_definition = schema_definition
        print("\n")
        print("USING UPDATED SYNTHETIC DATA AGENT")
        print("\n")

        logger.debug(
            "Initialized SyntheticDataAgent for schema '%s'",
            self.schema_name,
        )

    def generate_payload(self) -> Any:

        logger.debug(
            "Generating payload for schema '%s'",
            self.schema_name,
        )

        try:

            payload = self._generate_from_schema(
                self.schema_definition
            )

            logger.info(
                "Generated payload for schema '%s'",
                self.schema_name,
            )

            return payload

        except SyntheticDataError:
            raise

        except Exception as exc:

            logger.exception(
                "Failed to generate payload for schema '%s'",
                self.schema_name,
            )

            raise SyntheticDataError(
                f"Failed to generate payload: {exc}"
            ) from exc

    def _generate_from_schema(
        self,
        schema: Dict[str, Any],
    ) -> Any:

        if not isinstance(schema, dict):
            logger.error(
                "Schema is not a dictionary: %r",
                schema,
            )
            raise SyntheticDataError(
                "Schema definition must be a dictionary."
            )

        if "enum" in schema:
            return self._generate_enum_value(
                schema["enum"]
            )

        if "$ref" in schema:

            ref_name = (
                str(schema["$ref"])
                .split("/")[-1]
            )

            logger.info(
                "Generating placeholder object for reference %s",
                ref_name,
            )

            return self._generate_reference_object(
                ref_name
            )

        schema_type = schema.get("type")

        if isinstance(schema_type, list):
            schema_type = (
                schema_type[0]
                if schema_type
                else None
            )

        if schema_type == "string":
            return self._generate_string(schema)

        if schema_type == "integer":
            return self._generate_integer(schema)

        if schema_type == "number":
            return self._generate_number(schema)

        if schema_type == "boolean":
            return self._generate_boolean(schema)

        if schema_type == "array":
            return self._generate_array(schema)

        if schema_type == "object" or "properties" in schema:
            return self._generate_object(schema)

        logger.warning(
            "Unsupported or missing type for schema, defaulting to string: %r",
            schema,
        )

        return self._generate_string(schema)

    def _generate_enum_value(
        self,
        enum_values: Any,
    ) -> Any:

        if not isinstance(enum_values, list) or not enum_values:
            raise SyntheticDataError(
                "Enum definition must be a non-empty list."
            )

        return enum_values[0]

    def _generate_string(
        self,
        schema: Dict[str, Any],
    ) -> str:

        if schema.get("format") == "date-time":
            return "2025-01-01T00:00:00Z"

        if schema.get("format") == "date":
            return "2025-01-01"

        if schema.get("format") == "email":
            return "user@example.com"

        if schema.get("format") == "uuid":
            return "123e4567-e89b-12d3-a456-426614174000"

        return schema.get(
            "default",
            "sample_text",
        )

    def _generate_integer(
        self,
        schema: Dict[str, Any],
    ) -> int:

        default = schema.get("default")

        if isinstance(default, int) and not isinstance(default, bool):
            return default

        minimum = schema.get("minimum")

        if isinstance(minimum, int) and not isinstance(minimum, bool):
            return minimum

        return 1

    def _generate_number(
        self,
        schema: Dict[str, Any],
    ) -> float:

        default = schema.get("default")

        if isinstance(default, (int, float)) and not isinstance(default, bool):
            return float(default)

        minimum = schema.get("minimum")

        if isinstance(minimum, (int, float)) and not isinstance(minimum, bool):
            return float(minimum)

        return 1.0

    def _generate_boolean(
        self,
        schema: Dict[str, Any],
    ) -> bool:

        default = schema.get("default")

        if isinstance(default, bool):
            return default

        return True

    def _generate_array(
        self,
        schema: Dict[str, Any],
    ) -> List[Any]:

        items_schema = schema.get("items")

        if not isinstance(items_schema, dict):
            return []

        return [
            self._generate_from_schema(
                items_schema
            )
        ]

    def _generate_object(
        self,
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:

        properties = schema.get(
            "properties",
            {},
        )

        if not isinstance(properties, dict):
            return {}

        payload: Dict[str, Any] = {}

        for property_name, property_schema in properties.items():

            if not isinstance(property_schema, dict):
                continue

            payload[property_name] = (
                self._generate_from_schema(
                    property_schema
                )
            )

        return payload

    def _generate_reference_object(
        self,
        ref_name: str,
    ) -> Dict[str, Any]:
        """
        Generate placeholder objects for OpenAPI references.
        """

        if ref_name.lower() == "category":
            return {
                "id": 1,
                "name": "sample_category",
            }

        if ref_name.lower() == "tag":
            return {
                "id": 1,
                "name": "sample_tag",
            }

        return {
            "id": 1,
            "name": f"sample_{ref_name.lower()}",
        }