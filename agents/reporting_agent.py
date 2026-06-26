import csv
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ReportingAgent:
    """
    Generates execution reports for API test runs.
    """

    def __init__(
        self,
        output_directory: str = "reports",
    ) -> None:

        self.output_directory = Path(
            output_directory
        )

        self.output_directory.mkdir(
            exist_ok=True
        )

    def generate_csv_report(
        self,
        results: List[Dict[str, Any]],
    ) -> Path:
        """
        Generate CSV execution report.
        """

        report_path = (
            self.output_directory
            / "api_execution_report.csv"
        )

        headers = [
            "API",
            "Status Code",
            "Response Time (ms)",
            "Execution Status",
            "Response Validation",
            "Swagger Validation",
            "Risk",
            "Skip Reason",
        ]

        summary = {
            "total_apis": 0,
            "executed": 0,
            "skipped": 0,
            "execution_pass": 0,
            "execution_fail": 0,
            "response_validation_pass": 0,
            "response_validation_fail": 0,
            "swagger_validation_pass": 0,
            "swagger_validation_fail": 0,
            "total_response_time_ms": 0.0,
        }

        with report_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as csv_file:

            writer = csv.writer(csv_file)
            writer.writerow(headers)

            for result in results:
                api_column = self._format_api(
                    result.get("method"),
                    result.get("path"),
                )
                execution_status = result.get(
                    "execution_status",
                    "Executed",
                )
                risk = self._determine_risk(
                    result.get("status_code")
                )

                writer.writerow(
                    [
                        api_column,
                        result.get("status_code"),
                        result.get("response_time_ms"),
                        execution_status,
                        result.get("response_validation"),
                        result.get("swagger_validation"),
                        risk,
                        result.get("skip_reason"),
                    ]
                )

                summary["total_apis"] += 1
                if execution_status == "Executed":
                    summary["executed"] += 1
                    summary["total_response_time_ms"] += self._safe_float(
                        result.get("response_time_ms")
                    )
                    if result.get("success") is True:
                        summary["execution_pass"] += 1
                    else:
                        summary["execution_fail"] += 1
                    if self._is_pass(result.get("response_validation")):
                        summary["response_validation_pass"] += 1
                    else:
                        summary["response_validation_fail"] += 1
                    if self._is_pass(result.get("swagger_validation")):
                        summary["swagger_validation_pass"] += 1
                    else:
                        summary["swagger_validation_fail"] += 1
                else:
                    summary["skipped"] += 1

            writer.writerow([])
            writer.writerow(["Execution Summary", ""])
            writer.writerow(["Total APIs Planned", summary["total_apis"]])
            writer.writerow(["Executed", summary["executed"]])
            writer.writerow(["Skipped", summary["skipped"]])
            writer.writerow([
                "Execution Status PASS",
                summary["execution_pass"],
            ])
            writer.writerow([
                "Execution Status FAIL",
                summary["execution_fail"],
            ])
            writer.writerow([
                "Response Validation PASS",
                summary["response_validation_pass"],
            ])
            writer.writerow([
                "Response Validation FAIL",
                summary["response_validation_fail"],
            ])
            writer.writerow([
                "Swagger Validation PASS",
                summary["swagger_validation_pass"],
            ])
            writer.writerow([
                "Swagger Validation FAIL",
                summary["swagger_validation_fail"],
            ])
            pass_rate = (
                round(
                    (summary["execution_pass"] / summary["executed"]) * 100,
                    2,
                )
                if summary["executed"] > 0
                else 0.0
            )
            writer.writerow([
                "Pass Rate",
                f"{pass_rate}%",
            ])
            average_response_time = (
                summary["total_response_time_ms"]
                / summary["executed"]
                if summary["executed"] > 0
                else 0.0
            )
            writer.writerow(
                [
                    "Average Response Time (ms)",
                    round(average_response_time, 2),
                ]
            )

        logger.info(
            "CSV report generated: %s",
            report_path,
        )

        return report_path

    @staticmethod
    def _format_api(
        method: Any,
        path: Any,
    ) -> str:
        method_str = str(method).strip().upper() if method is not None else ""
        path_str = str(path).strip() if path is not None else ""
        return f"{method_str} {path_str}".strip()

    @staticmethod
    def _format_execution_status(
        success: Any,
    ) -> str:
        if isinstance(success, str):
            normalized = success.strip().lower()
            if normalized in {"true", "pass", "passed", "yes"}:
                return "PASS"
            if normalized in {"false", "fail", "failed", "no"}:
                return "FAIL"
        if isinstance(success, bool):
            return "PASS" if success else "FAIL"
        return "FAIL"

    @staticmethod
    def _determine_risk(
        status_code: Any,
    ) -> str:
        try:
            code = int(status_code)
        except (TypeError, ValueError):
            return "UNKNOWN"
        if 200 <= code < 300:
            return "LOW"
        if 400 <= code < 500:
            return "MEDIUM"
        if 500 <= code < 600:
            return "HIGH"
        return "UNKNOWN"

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _is_pass(value: Any) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"true", "pass", "passed", "yes"}
        if isinstance(value, bool):
            return value
        return False