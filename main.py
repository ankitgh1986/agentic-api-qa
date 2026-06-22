import json
import logging
from pathlib import Path
from typing import Any, Iterable, List, Dict

from agents.scenario_generation_agent import ScenarioGenerationAgent
from agents.swagger_parser_agent import OpenAPIValidationError, SwaggerParserAgent

LOG_FORMAT = "%(levelname)s: %(asctime)s - %(name)s - %(message)s"
SPEC_PATH = Path("targets/petstore.json")


def configure_logging() -> None:
    """Configure application logging for the QA framework."""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("chardet").setLevel(logging.WARNING)


def format_api_table(operations: Iterable[Dict[str, object]]) -> str:
    """Format the extracted API operations into a fixed-width table."""
    lines: List[str] = []
    header_method = "Method"
    header_path = "Path"
    method_width = max((len(str(op.get("method", ""))) for op in operations), default=len(header_method))
    method_width = max(method_width, len(header_method))
    path_width = max((len(str(op.get("path", ""))) for op in operations), default=len(header_path))
    path_width = max(path_width, len(header_path))

    lines.append(f"{header_method:<{method_width}}   {header_path}")
    lines.append(f"{('-' * method_width):<{method_width}}   {('-' * path_width)}")

    for operation in operations:
        method = str(operation.get("method", ""))
        path = str(operation.get("path", ""))
        lines.append(f"{method:<{method_width}}   {path}")

    return "\n".join(lines)


def print_discovery_report(operations: List[Dict[str, object]]) -> None:
    """Print the final QA framework report for discovered API operations."""
    print("=" * 39)
    print("AGENTIC API QA FRAMEWORK v0.1")
    print("=" * 39)
    print()
    print(f"OpenAPI File : {SPEC_PATH.as_posix()}")
    print()
    print(f"Total APIs Discovered : {len(operations)}")
    print()
    print(format_api_table(operations))
    print()
    print("=" * 39)


def print_report(operations: List[Dict[str, object]]) -> None:
    """Alias for the reusable discovery report printer."""
    print_discovery_report(operations)


def print_scenario_report(scenarios: List[Dict[str, Any]]) -> None:
    """Print detailed scenario output for each discovered API."""
    for scenario_definition in scenarios:
        api = scenario_definition.get("api", "")
        method = scenario_definition.get("method", "")
        positive_scenarios = scenario_definition.get("positive_scenarios", [])
        negative_scenarios = scenario_definition.get("negative_scenarios", [])
        validation_scenarios = scenario_definition.get("validation_scenarios", [])

        print("=" * 50)
        print(f"API: {method} {api}")
        print("=" * 50)
        print()
        print("Positive Scenarios:")
        for scenario in positive_scenarios:
            print(f"- {scenario}")
        print()
        print("Negative Scenarios:")
        for scenario in negative_scenarios:
            print(f"- {scenario}")
        print()
        print("Validation Scenarios:")
        for scenario in validation_scenarios:
            print(f"- {scenario}")
        print()


def load_operations() -> List[Dict[str, object]]:
    """Load the OpenAPI specification and return all parsed operations."""
    parser = SwaggerParserAgent(SPEC_PATH)
    return parser.get_operations()


def generate_scenarios(operations: List[Dict[str, object]]) -> List[Dict[str, Any]]:
    """Generate test scenarios from parsed OpenAPI operations."""
    generator = ScenarioGenerationAgent(operations)
    return generator.generate_scenarios()


def main() -> None:
    """Main entry point for the Agentic API QA framework."""
    configure_logging()
    logger = logging.getLogger(__name__)

    try:
        operations = load_operations()
        print_discovery_report(operations)
        logger.info("Successfully discovered %d API operations.", len(operations))

        scenario_definitions = generate_scenarios(operations)
        print_scenario_report(scenario_definitions)
        logger.info("Successfully generated scenarios for %d API operations.", len(scenario_definitions))
    except FileNotFoundError as exc:
        logger.error("OpenAPI specification file could not be found: %s", exc)
        print(f"ERROR: OpenAPI specification file not found: {SPEC_PATH.as_posix()}")
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse OpenAPI JSON: %s", exc)
        print(f"ERROR: Invalid JSON content in {SPEC_PATH.as_posix()}")
    except OpenAPIValidationError as exc:
        logger.error("OpenAPI validation failed: %s", exc)
        print(f"ERROR: OpenAPI validation failed: {exc}")
    except Exception as exc:  # pragma: no cover
        logger.exception("Unexpected error while discovering API operations.")
        print(f"ERROR: Unexpected failure: {exc}")


if __name__ == "__main__":
    main()
