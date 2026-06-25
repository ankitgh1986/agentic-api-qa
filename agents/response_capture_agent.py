import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ResponseCaptureAgent:
    """
    Extracts meaningful values from successful API responses and stores them in
    the provided StateManagerAgent.
    """

    ENTITY_KEY_MAP = {
        "/pet": "petId",
        "/user": "userId",
        "/store/order": "orderId",
    }

    def capture(
        self,
        operation: Dict[str, Any],
        execution_result: Dict[str, Any],
        state_manager: Any,
    ) -> None:
        """
        Capture values from a successful API execution result.

        Args:
            operation: Metadata describing the API operation.
            execution_result: Result returned from ExecutionAgent.
            state_manager: Instance of StateManagerAgent for storing values.
        """
        status_code = execution_result.get("status_code")
        response_body = execution_result.get("response_body")
        path = str(operation.get("path", ""))

        if not self._is_success(status_code):
            logger.debug(
                "Skipping capture for non-successful response: %s %s",
                path,
                status_code,
            )
            return

        if not isinstance(response_body, dict):
            logger.debug(
                "Skipping capture for non-dictionary response body: %s",
                type(response_body).__name__,
            )
            return

        entity_key = self._infer_entity_key(path)

        if entity_key and "id" in response_body:
            capture_value = response_body["id"]
            state_manager.set(entity_key, capture_value)
            logger.info(
                "Captured %s from %s: %s",
                entity_key,
                path,
                capture_value,
            )

        if "username" in response_body:
            username_value = response_body["username"]
            state_manager.set("username", username_value)
            logger.info(
                "Captured username from %s: %s",
                path,
                username_value,
            )

    @staticmethod
    def _is_success(status_code: Optional[Any]) -> bool:
        try:
            code = int(status_code)
        except (TypeError, ValueError):
            return False
        return 200 <= code < 300

    @classmethod
    def _infer_entity_key(cls, path: str) -> Optional[str]:
        normalized_path = path.strip().lower()
        for prefix, key in cls.ENTITY_KEY_MAP.items():
            if normalized_path.startswith(prefix):
                return key
        return None
