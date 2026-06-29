import logging
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


class ExecutionGroupingAgent:
    """
    Builds execution groups from operations and their dependency graph.
    Uses topological layering to ensure dependent operations are
    executed in correct order.
    """

    @staticmethod
    def build_execution_groups(
        operations: List[Dict[str, Any]],
        dependency_graph: Dict[str, List[str]],
    ) -> List[List[Dict[str, Any]]]:
        """
        Build execution groups from operations based on dependency graph.

        Operations with no unresolved parent dependencies are placed in the same
        execution group. Dependent operations appear in later groups.

        Args:
            operations: List of operation dictionaries with 'method' and 'path'.
            dependency_graph: Dict mapping parent operation keys to lists of
                             child operation keys. Format:
                             "METHOD /path" -> ["METHOD /child_path", ...]

        Returns:
            List[List[Dict]]: Each inner list represents one execution batch.
                             Operations within a batch can execute independently.

        Example:
            operations = [
                {"method": "GET", "path": "/pets"},
                {"method": "POST", "path": "/pets"},
                {"method": "GET", "path": "/pets/1"},
            ]
            dependency_graph = {
                "GET /pets": ["POST /pets"],
                "POST /pets": ["GET /pets/1"],
            }
            result = ExecutionGroupingAgent.build_execution_groups(
                operations, dependency_graph
            )
            # Returns: [[GET /pets], [POST /pets], [GET /pets/1]]
        """
        if not operations:
            logger.info("No operations to group.")
            return []

        # Create a mapping of operation key to operation dict
        operation_map: Dict[str, Dict[str, Any]] = {}
        for op in operations:
            method = op.get("method", "").upper()
            path = op.get("path", "")
            op_key = f"{method} {path}"
            operation_map[op_key] = op

        # Build a reverse dependency map: child -> [parents]
        parent_map: Dict[str, List[str]] = {}
        for parent, children in dependency_graph.items():
            for child in children:
                if child not in parent_map:
                    parent_map[child] = []
                parent_map[child].append(parent)

        # Track which operations have been assigned to groups
        assigned_operations: Set[str] = set()

        # List to store execution groups
        execution_groups: List[List[Dict[str, Any]]] = []

        # Continue until all operations are assigned
        while len(assigned_operations) < len(operation_map):
            # Snapshot of previously assigned operations
            previously_assigned = assigned_operations.copy()
            
            current_group: List[Dict[str, Any]] = []

            # Find operations with no unresolved parent dependencies
            for op_key, operation in operation_map.items():
                if op_key in assigned_operations:
                    continue

                # Get parent dependencies for this operation
                parents = parent_map.get(op_key, [])

                # Check if all parents have been assigned (against snapshot)
                if all(parent in previously_assigned for parent in parents):
                    current_group.append(operation)

            # If no operations were added, we have a cycle or no operations
            if not current_group:
                unassigned = set(operation_map.keys()) - assigned_operations
                logger.warning(
                    f"Circular dependency detected. Unresolved operations: "
                    f"{unassigned}"
                )
                break

            # Add all operations in current_group to assigned_operations
            for operation in current_group:
                method = operation.get("method", "").upper()
                path = operation.get("path", "")
                op_key = f"{method} {path}"
                assigned_operations.add(op_key)

            execution_groups.append(current_group)

        # Log execution group information
        logger.info(f"Number of execution groups created: {len(execution_groups)}")

        for idx, group in enumerate(execution_groups, 1):
            group_size = len(group)
            group_ops = [
                f"{op.get('method', '').upper()} {op.get('path', '')}"
                for op in group
            ]
            logger.info(f"Execution group {idx}: {group_size} operation(s)")
            logger.info(f"  Members: {group_ops}")

        return execution_groups
