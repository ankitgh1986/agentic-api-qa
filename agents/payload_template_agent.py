import logging
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)


class PayloadTemplateAgent:
    """
    Converts generated payload objects into runtime-aware payload templates.
    """

    TEMPLATE_KEYS = {
        "id": "{{userId}}",
        "petId": "{{petId}}",
        "orderId": "{{orderId}}",
        "username": "{{username}}",
    }

    def create_template(
        self,
        payload: Any,
    ) -> Any:
        """
        Create a templated copy of the provided payload.

        Args:
            payload: The generated payload to transform.

        Returns:
            A new payload object with runtime template values applied.
        """
        return self._template_value(payload)

    def _template_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return self._template_dict(value)

        if isinstance(value, list):
            return self._template_list(value)

        return value

    def _template_dict(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        templated: Dict[str, Any] = {}

        for key, value in payload.items():
            if key in self.TEMPLATE_KEYS:
                templated_value = self.TEMPLATE_KEYS[key]
                logger.info(
                    "Templated field %s = %s",
                    key,
                    templated_value,
                )
                templated[key] = templated_value
                continue

            templated[key] = self._template_value(value)

        return templated

    def _template_list(self, payload: List[Any]) -> List[Any]:
        return [self._template_value(item) for item in payload]
