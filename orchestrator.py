import logging
from pathlib import Path
from typing import Any, Dict, List

from agents.swagger_parser_agent import SwaggerParserAgent
from agents.execution_agent import ExecutionAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(asctime)s - %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)

SPEC_PATH = Path("targets/petstore.json")
BASE_URL = "https://petstore3.swagger.io/api/v3"


def load_operations() -> List[Dict[str, Any]]:
    """
    Load operations from Swagger/OpenAPI spec.
    """
    parser = SwaggerParserAgent(SPEC_PATH)
    return parser.get_operations()


def get_get_operations(
    operations: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Return only GET operations.
    """
    return [
        operation
        for operation in operations
        if operation.get("method") == "GET"
    ]


def execute_operations(
    operations: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Execute all supplied operations.
    """
    execution_agent = ExecutionAgent(
        base_url=BASE_URL
    )

    results = []

    for operation in operations:
        print(
            f"\nExecuting {operation['method']} {operation['path']}"
        )

        result = execution_agent.execute_operation(
            operation=operation
        )

        results.append(result)

        status = result.get("status_code")

        print(
            f"Status Code : {status}"
        )

    return results


def print_summary(
    results: List[Dict[str, Any]]
) -> None:
    """
    Print execution summary.
    """
    total = len(results)

    passed = sum(
        1
        for result in results
        if result.get("success")
    )

    failed = total - passed

    print("\n" + "=" * 50)
    print("EXECUTION SUMMARY")
    print("=" * 50)

    print(f"Total APIs Executed : {total}")
    print(f"Passed              : {passed}")
    print(f"Failed              : {failed}")

    print("=" * 50)


def main() -> None:
    """
    Framework entry point.
    """
    print("=" * 50)
    print("AGENTIC API QA FRAMEWORK - SPRINT 5.1")
    print("=" * 50)

    operations = load_operations()

    get_operations = get_get_operations(
        operations
    )

    print(
        f"\nTotal GET APIs Found : {len(get_operations)}"
    )

    results = execute_operations(
        get_operations
    )

    print_summary(
        results
    )


if __name__ == "__main__":
    main()