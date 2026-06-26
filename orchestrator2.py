import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.execution_agent import ExecutionAgent
from agents.schema_resolver_agent import SchemaResolverAgent
from agents.swagger_parser_agent import SwaggerParserAgent
from agents.synthetic_data_agent import SyntheticDataAgent
from agents.response_validator_agent import ResponseValidatorAgent
from agents.response_capture_agent import ResponseCaptureAgent
from agents.state_manager_agent import StateManagerAgent
from agents.payload_template_agent import PayloadTemplateAgent
from agents.planning_agent import ExecutionPlannerAgent
from agents.swagger_response_validator_agent import SwaggerResponseValidatorAgent
from agents.reporting_agent import ReportingAgent

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
) -> tuple[List[Dict[str, Any]], StateManagerAgent]:
    """
    Execute all supported operations.
    """

    state_manager = StateManagerAgent()
    execution_agent = ExecutionAgent(
        base_url=BASE_URL,
        state_manager=state_manager,
    )

    validator = ResponseValidatorAgent()
    response_capture_agent = ResponseCaptureAgent()
    payload_template_agent = PayloadTemplateAgent()

    swagger_validator = (
        SwaggerResponseValidatorAgent()
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

            # Convert generated payload into a runtime-aware template
            try:
                payload = payload_template_agent.create_template(payload)
            except Exception:
                logger.exception("Failed to create payload template; proceeding with original payload.")

        result = execution_agent.execute_operation(
            operation=operation,
            payload=payload,
        )

        response_capture_agent.capture(
            operation,
            result,
            state_manager,
        )

        validation_result = validator.validate(
            result
        )

        swagger_validation = (
            swagger_validator.validate(
                operation,
                result,
            )
        )

        print("\nValidation Result:")

        for item in validation_result["validations"]:

            status = (
                "PASS"
                if item["passed"]
                else "FAIL"
            )

            print(
                f"{item['check']} : {status}"
            )

        print(
            "Overall Validation : "
            f"{'PASS' if validation_result['passed'] else 'FAIL'}"
        )

        print("\nSwagger Validation:")

        for item in swagger_validation["validations"]:

            status = (
                "PASS"
                if item["passed"]
                else "FAIL"
            )

            print(
                f"{item['check']} : {status}"
            )

            print(
                f"Expected : {item['expected']}"
            )

            print(
                f"Actual : {item['actual']}"
            )

        result["response_validation"] = (
            "PASS"
            if validation_result["passed"]
            else "FAIL"
        )

        result["swagger_validation"] = (
            "PASS"
            if swagger_validation["passed"]
            else "FAIL"
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

    return results, state_manager


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
        "AGENTIC API QA FRAMEWORK - SPRINT 11.0"
    )
    print("=" * 60)

    operations = load_operations()

    supported_operations = (
        get_supported_operations(
            operations
        )
    )

    execution_planner_agent = ExecutionPlannerAgent()
    planned_operations = execution_planner_agent.plan_execution(
        supported_operations
    )

    print(
        f"\nTotal Supported APIs : "
        f"{len(supported_operations)}"
    )

    print("\nPlanned execution order:")
    for idx, operation in enumerate(planned_operations, start=1):
        print(
            f"{idx}. {operation.get('method', '').upper()} {operation.get('path', '')}"
        )

    results, state_manager = execute_operations(
        planned_operations
    )

    print_summary(
        results
    )

    reporting_agent = ReportingAgent()

    report_path = reporting_agent.generate_csv_report(
        results
    )

    print(
        "\nRuntime State----------------",
        state_manager.dump(),
    )

    print(
        f"\nCSV Report Generated : {report_path}"
    )


if __name__ == "__main__":
    main()