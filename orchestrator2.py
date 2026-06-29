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
from agents.execution_decision_agent import ExecutionDecisionAgent
from agents.retry_decision_agent import RetryDecisionAgent
from agents.swagger_response_validator_agent import SwaggerResponseValidatorAgent
from agents.reporting_agent import ReportingAgent
from agents.ExecutionGroupingAgent import ExecutionGroupingAgent
from agents.parallel_execution_agent import ParallelExecutionAgent

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
    operations: List[Dict[str, Any]],
    dependency_graph: Dict[str, List[str]],
) -> tuple[List[Dict[str, Any]], StateManagerAgent]:
    """
    Execute all supported operations.
    """
    # Prepare runtime agents and state
    state_manager = StateManagerAgent()
    execution_agent = ExecutionAgent(
        base_url=BASE_URL,
        state_manager=state_manager,
    )

    decision_agent = ExecutionDecisionAgent()
    retry_decision_agent = RetryDecisionAgent()
    validator = ResponseValidatorAgent()
    response_capture_agent = ResponseCaptureAgent()
    payload_template_agent = PayloadTemplateAgent()

    swagger_validator = SwaggerResponseValidatorAgent()

    parallel_execution_agent = ParallelExecutionAgent()

    results: List[Dict[str, Any]] = []
    execution_results: Dict[str, Dict[str, Any]] = {}

    # Build execution groups from dependency graph
    execution_groups = ExecutionGroupingAgent.build_execution_groups(
        operations,
        dependency_graph,
    )

    # Helper to execute a single operation (used by the parallel agent)
    def execute_single_operation(operation: Dict[str, Any]) -> Dict[str, Any]:
        method = operation.get("method")
        path = operation.get("path")
        operation_identifier = f"{str(method).upper()} {path}"

        should_run = decision_agent.should_execute(
            operation_identifier,
            execution_results,
            dependency_graph,
        )

        if not should_run:
            failure_parents = [
                parent
                for parent, dependents in dependency_graph.items()
                if operation_identifier in dependents
                and not execution_results.get(parent, {}).get("success", False)
            ]
            skip_reason = (
                f"Parent {failure_parents[0]} failed"
                if failure_parents
                else "Dependency failed"
            )

            skip_result = {
                "method": method,
                "path": path,
                "url": None,
                "status_code": None,
                "response_time_ms": None,
                "success": False,
                "response_body": None,
                "error": None,
                "response_validation": None,
                "swagger_validation": None,
                "execution_status": "Skipped",
                "skip_reason": skip_reason,
            }

            retry_decision = retry_decision_agent.should_retry(
                skip_result
            )
            skip_result["retry"] = retry_decision["retry"]
            skip_result["retry_reason"] = retry_decision["reason"]
            skip_result["retry_category"] = retry_decision.get("category")

            logger.info(
                "Skipped operation due to dependency failure: %s (%s)",
                operation_identifier,
                skip_reason,
            )

            print("\nRetry Decision--------------")
            print(
                f"Retry   : {'YES' if skip_result['retry'] else 'NO'}"
            )
            print(
                f"Reason  : {skip_result['retry_reason']}"
            )

            return skip_result

        # Execution
        payload = build_payload(operation)

        if payload:
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

        result["execution_status"] = "Executed"
        result["skip_reason"] = ""

        validation_result = validator.validate(result)

        swagger_validation = swagger_validator.validate(operation, result)

        result["response_validation"] = (
            "PASS" if validation_result["passed"] else "FAIL"
        )

        result["swagger_validation"] = (
            "PASS" if swagger_validation["passed"] else "FAIL"
        )

        retry_decision = retry_decision_agent.should_retry(result)
        result["retry"] = retry_decision["retry"]
        result["retry_reason"] = retry_decision["reason"]
        result["retry_category"] = retry_decision.get("category")

        print("\nRetry Decision--------------")
        print(
            f"Retry   : {'YES' if result['retry'] else 'NO'}"
        )
        print(
            f"Reason  : {result['retry_reason']}"
        )

        return result

    # Execute groups sequentially; operations inside a group run concurrently
    for idx, group in enumerate(execution_groups, start=1):
        print("\n" + "=" * 60)
        print(f"EXECUTING GROUP {idx} / {len(execution_groups)}")
        print("=" * 60)

        group_results = parallel_execution_agent.execute_group(
            operations=group,
            execute_func=execute_single_operation,
        )

        # Extend overall results and update execution_results map
        for res in group_results:
            method = res.get("method")
            path = res.get("path")
            op_key = f"{str(method).upper()} {path}"
            results.append(res)
            execution_results[op_key] = res

    return results, state_manager


def print_summary(
    results: List[Dict[str, Any]]
) -> None:
    """
    Print execution summary.
    """

    total = len(results)
    skipped = sum(
        1
        for result in results
        if result.get("execution_status") == "Skipped"
    )
    executed = total - skipped
    passed = sum(
        1
        for result in results
        if result.get("execution_status") == "Executed"
        and result.get("success")
    )
    failed = sum(
        1
        for result in results
        if result.get("execution_status") == "Executed"
        and not result.get("success")
    )

    pass_rate = (
        round(
            (passed / executed) * 100,
            2,
        )
        if executed
        else 0
    )

    print("\n")
    print("=" * 60)
    print("EXECUTION SUMMARY")
    print("=" * 60)

    print(
        f"Total APIs Planned : {total}"
    )

    print(
        f"Executed            : {executed}"
    )

    print(
        f"Skipped             : {skipped}"
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


def print_execution_groups(
    execution_groups: List[List[Dict[str, Any]]]
) -> None:
    """
    Print execution groups in a readable format.
    """

    if not execution_groups:
        print("\nNo execution groups generated.")
        return

    separator = "=" * 60
    print("\n" + separator + "EXECUTION GROUPS" + separator)

    for group_idx, group in enumerate(
        execution_groups, 1
    ):
        print(f"Group {group_idx}")
        print("-" * 60)

        for operation in group:
            method = operation.get(
                "method", ""
            ).upper()
            path = operation.get("path", "")
            print(f"{method} {path}")

    print(separator)


def main() -> None:

    print("=" * 60)
    print(
        "AGENTIC API QA FRAMEWORK - SPRINT 13.0"
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

    dependency_graph = execution_planner_agent.dependency_graph

    # Execute all operations (grouped and parallelized inside)
    results, state_manager = execute_operations(
        planned_operations,
        dependency_graph,
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