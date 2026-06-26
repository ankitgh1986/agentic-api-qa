import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ExecutionDecisionAgent:
    """
    Decides whether an API operation should be executed based on
    prior execution results and dependency relationships.
    """

    def should_execute(
        self,
        operation_identifier: str,
        execution_results: Dict[str, Any],
        dependency_graph: Dict[str, Any],
    ) -> bool:
        """
        Determine if the given operation should execute.

        Args:
            operation_identifier: Operation identifier string.
            execution_results: Mapping of operation identifiers to results.
            dependency_graph: Dependency graph produced by ExecutionDependencyAgent.

        Returns:
            True when execution should proceed, otherwise False.
        """
        parents = [
            parent
            for parent, dependents in dependency_graph.items()
            if operation_identifier in dependents
        ]

        if not parents:
            logger.info(
                "Decision for %s: no parent dependencies, execute=True",
                operation_identifier,
            )
            return True

        for parent in parents:
            result = execution_results.get(parent, {})
            if not result.get("success", False):
                logger.info(
                    "Decision for %s: parent %s failed, execute=False",
                    operation_identifier,
                    parent,
                )
                return False

        logger.info(
            "Decision for %s: all parent dependencies passed, execute=True",
            operation_identifier,
        )
        return True
