import logging
import time
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class ParallelExecutionAgentError(Exception):
    """Base exception for ParallelExecutionAgent."""


class ParallelExecutionAgent:
    """
    Executes operations in an execution group concurrently using ThreadPoolExecutor.

    This agent is independent from the rest of the framework and does not
    assume knowledge about Swagger, validation, payload generation, or reporting.
    """

    def __init__(
        self,
        max_workers: int = 4,
    ) -> None:
        """
        Initialize the parallel execution agent.

        Args:
            max_workers: Maximum number of worker threads. Default is 4.
        """
        self.max_workers = max_workers

    def execute_group(
        self,
        operations: List[Dict[str, Any]],
        execute_func: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Execute all operations in a group concurrently.

        Args:
            operations: List of operation dictionaries to execute.
            execute_func: Callable that executes a single operation and
                         returns a result dictionary.

        Returns:
            List of execution result dictionaries in completion order.
            If an exception occurs during execution, it is caught and logged,
            and a result dictionary with error information is included.

        Raises:
            ParallelExecutionAgentError: If the operations list is empty.
        """
        if not operations:
            # No operations to execute; return empty results list.
            logger.info("No operations provided to execute; returning empty list.")
            return []

        group_size = len(operations)
        # Compute worker count based on configured max and group size
        worker_count = min(self.max_workers, group_size)

        logger.info(
            f"Starting parallel execution of {group_size} operation(s) "
            f"with {worker_count} worker thread(s)."
        )

        start_time = time.time()
        results: List[Dict[str, Any]] = []
        future_to_operation: Dict[Any, Dict[str, Any]] = {}

        try:
            with ThreadPoolExecutor(
                max_workers=worker_count
            ) as executor:
                # Submit all operations
                for operation in operations:
                    method = operation.get("method", "").upper()
                    path = operation.get("path", "")
                    operation_id = f"{method} {path}"

                    logger.info(
                        f"Submitted operation: {operation_id}"
                    )

                    future = executor.submit(
                        execute_func,
                        operation,
                    )
                    future_to_operation[future] = operation

                # Collect results as they complete
                for future in as_completed(
                    future_to_operation.keys()
                ):
                    operation = future_to_operation[future]
                    method = operation.get("method", "").upper()
                    path = operation.get("path", "")
                    operation_id = f"{method} {path}"

                    try:
                        result = future.result()
                        logger.info(
                            f"Completed operation: {operation_id}"
                        )
                        results.append(result)

                    except Exception as exc:
                        logger.exception(
                            f"Exception during execution of {operation_id}: "
                            f"{exc}"
                        )

                        # Create error result to include in results
                        error_result = {
                            "method": method,
                            "path": path,
                            "status_code": None,
                            "response_time_ms": None,
                            "success": False,
                            "response_body": None,
                            "error": str(exc),
                            "execution_status": "Failed",
                            "skip_reason": "",
                        }
                        results.append(error_result)

        except Exception as exc:
            logger.exception(
                f"Unexpected error in thread pool execution: {exc}"
            )
            raise ParallelExecutionAgentError(
                f"Parallel execution failed: {exc}"
            ) from exc

        elapsed_time = time.time() - start_time
        elapsed_ms = round(elapsed_time * 1000, 2)

        logger.info(
            f"Group execution completed in {elapsed_ms} ms. "
            f"Processed {len(results)} operation(s)."
        )

        return results
