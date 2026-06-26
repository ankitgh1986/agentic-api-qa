import logging
from typing import Any, Dict, List

from agents.execution_dependency_agent import ExecutionDependencyAgent

logger = logging.getLogger(__name__)


class ExecutionPlannerAgent:
    """
    Plans the optimal execution order for API operations.
    """

    EXECUTION_PRIORITY = [
        "POST",
        "GET",
        "PUT",
        "DELETE",
    ]

    def __init__(self) -> None:
        self.dependency_agent = ExecutionDependencyAgent()
        self.dependency_graph: Dict[str, List[str]] = {}

    def plan_execution(
        self,
        operations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Reorder operations by HTTP method priority.

        Args:
            operations: List of Swagger operation dictionaries.

        Returns:
            A new list of operations ordered by the execution strategy.
        """
        prioritized: List[Dict[str, Any]] = []
        remaining: List[Dict[str, Any]] = []

        for method in self.EXECUTION_PRIORITY:
            prioritized.extend(
                [
                    operation
                    for operation in operations
                    if str(operation.get("method", "")).upper() == method
                ]
            )

        remaining = [
            operation
            for operation in operations
            if str(operation.get("method", "")).upper() not in self.EXECUTION_PRIORITY
        ]

        self.dependency_graph = self.dependency_agent.build_dependency_graph(
            operations
        )
        logger.info(
            "Dependency graph discovered: %s",
            self.dependency_graph,
        )

        plan = prioritized + remaining
        logger.info(
            "Planned execution for %d operations.",
            len(plan),
        )
        return plan
