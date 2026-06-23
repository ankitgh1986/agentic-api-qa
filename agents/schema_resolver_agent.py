import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SchemaResolverAgent:
    """
    Resolves OpenAPI schema references and enriches API operations
    with request schema metadata.
    """

    def __init__(
        self,
        spec: Dict[str, Any],
        operations: List[Dict[str, Any]],
    ) -> None:

        self._spec = spec
        self._operations = operations

    def enrich_operations(self) -> List[Dict[str, Any]]:

        enriched_operations = []

        for operation in self._operations:

            operation_copy = dict(operation)

            schema_ref = operation.get(
                "request_schema_ref"
            )

            if schema_ref:
                operation_copy[
                    "request_schema"
                ] = self._resolve_schema(
                    schema_ref
                )

            else:
                operation_copy[
                    "request_schema"
                ] = {}

            enriched_operations.append(
                operation_copy
            )

        logger.info(
            "Enriched %d operations with schema metadata",
            len(enriched_operations),
        )

        return enriched_operations

    def _resolve_schema(
        self,
        schema_ref: str,
    ) -> Dict[str, Any]:

        if not schema_ref:
            return {}

        try:

            parts = (
                schema_ref
                .replace("#/", "")
                .split("/")
            )

            current = self._spec

            for part in parts:

                if not isinstance(current, dict):
                    return {}

                current = current.get(part)

                if current is None:
                    return {}

            if isinstance(current, dict):
                return current

            return {}

        except Exception:

            logger.exception(
                "Failed resolving schema %s",
                schema_ref,
            )

            return {}