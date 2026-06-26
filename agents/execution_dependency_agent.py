import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ExecutionDependencyAgent:
    """
    Discovers execution dependencies between Swagger API operations.
    """

    DEFAULT_DEPENDENCY_RULES = {
        "POST /user": [
            "GET /user/{username}",
            "PUT /user/{username}",
        ],
        "POST /pet": [
            "GET /pet/{petId}",
            "POST /pet/{petId}",
            "POST /pet/{petId}/uploadImage",
            "POST /store/order",
        ],
        "POST /store/order": [
            "GET /store/order/{orderId}",
        ],
    }

    def build_dependency_graph(
        self,
        operations: List[Dict[str, Any]],
    ) -> Dict[str, List[str]]:
        """
        Build a dependency graph for Swagger operations.

        Args:
            operations: List of Swagger operation dictionaries.

        Returns:
            A dependency graph mapping operation identifiers
            to their dependent operations.
        """

        graph: Dict[str, List[str]] = {}

        for operation in operations:

            identifier = self._operation_identifier(
                operation
            )

            graph[identifier] = self._find_dependents(
                identifier
            )

        dependency_count = sum(
            len(dependents)
            for dependents in graph.values()
        )

        logger.info(
            "Discovered %d dependency relationships.",
            dependency_count,
        )

        return graph

    def _operation_identifier(
        self,
        operation: Dict[str, Any],
    ) -> str:
        """
        Build a unique operation identifier.
        """

        method = str(
            operation.get(
                "method",
                "",
            )
        ).upper()

        path = str(
            operation.get(
                "path",
                "",
            )
        )

        return f"{method} {path}"

    def _find_dependents(
        self,
        identifier: str,
    ) -> List[str]:
        """
        Return dependent operations for the given identifier.
        """

        return self.DEFAULT_DEPENDENCY_RULES.get(
            identifier,
            [],
        )