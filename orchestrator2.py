import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.execution_agent import ExecutionAgent
from agents.schema_resolver_agent import SchemaResolverAgent
from agents.swagger_parser_agent import SwaggerParserAgent
from agents.synthetic_data_agent import SyntheticDataAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(asctime)s - %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)

SPEC_PATH = Path("targets/petstore.json")
BASE_URL = "https://petstore3.swagger.io/api/v3"

SUPPORTED_METHODS = {
    "GET",
    "POST",
    "PUT",
}


def load_operations() -> List[Dict[str, Any]]:
    """
    Load operations from Swagger and enrich with schema metadata.
    """

    parser = SwaggerParserAgent(
        SPEC_PATH
    )

    operations = parser.get_operations()

    resolver = SchemaResolverAgent(
        parser.get_spec(),
        operations,
    )

    enriched_operations = resolver.enrich_operations()

    return enriched_operations


def get_supported_operations(
    operations: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Filter only GET / POST / PUT APIs.
    """

    return [
        operation
        for operation in operations
        if str(
            operation.get("method", "")
        ).upper() in SUPPORTED_METHODS
    ]


def build_payload(
    operation: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Generate synthetic payload for POST/PUT APIs.
    """

    method = str(
        operation.get("method", "")
    ).upper()

    if method not in {"POST", "PUT"}:
        return None

    schema = operation.get(
        "request_schema"
    )

    if not isinstance(schema, dict):
        return None

    if not schema:
        return None

    schema_name = str(
        operation.get(
            "request_schema_ref",
            "GeneratedSchema",
        )
    ).split("/")[-1]

    try:

        generator = SyntheticDataAgent(
            schema_name=schema_name,
            schema_definition=schema,
        )

        payload = generator.generate_payload()

        if isinstance(payload, dict):
            return payload

    except Exception as exc:

        logger.exception(
            "Payload generation failed for %s %s",
            operation.get("method"),
            operation.get("path"),
        )

        print(
            f"Payload generation failed: {exc}"
        )

    return None


def execute_operations(
    operations: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Execute all supported operations.
    """

    execution_agent = ExecutionAgent(
        base_url=BASE_URL
    )

    results = []

    for operation in operations:

        method = operation["method"]
        path = operation["path"]

        print("\n" + "=" * 60)
        print(
            f"Executing {method} {path}"
        )
        print("=" * 60)

        payload = build_payload(
            operation
        )

        if payload:

            print("\nPayload:")
            print(payload)

        result = execution_agent.execute_operation(
            operation=operation,
            payload=payload,
        )

        results.append(result)

        print(
            f"\nStatus Code : "
            f"{result.get('status_code')}"
        )

        print(
            f"Response Time : "
            f"{result.get('response_time_ms')} ms"
        )

        if result.get("error"):

            print(
                f"Error : "
                f"{result.get('error')}"
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

    pass_rate = (
        round(
            (passed / total) * 100,
            2,
        )
        if total
        else 0
    )

    print("\n")
    print("=" * 60)
    print("EXECUTION SUMMARY")
    print("=" * 60)

    print(
        f"Total APIs Executed : {total}"
    )

    print(
        f"Passed              : {passed}"
    )

    print(
        f"Failed              : {failed}"
    )

    print(
        f"Pass Rate           : "
        f"{pass_rate}%"
    )

    print("=" * 60)


def main() -> None:

    print("=" * 60)
    print(
        "AGENTIC API QA FRAMEWORK - SPRINT 7.0"
    )
    print("=" * 60)

    operations = load_operations()

    supported_operations = (
        get_supported_operations(
            operations
        )
    )

    print(
        f"\nTotal Supported APIs : "
        f"{len(supported_operations)}"
    )

    results = execute_operations(
        supported_operations
    )

    print_summary(
        results
    )


if __name__ == "__main__":
    main()