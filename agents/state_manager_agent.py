import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class StateManagerAgentError(Exception):
    """Base exception for StateManagerAgent."""


class StateManagerAgent:
    """
    Shared runtime state manager for the Agentic API QA Framework.

    This agent maintains an internal dictionary that can be used as
    shared memory between framework components during test execution.
    """

    def __init__(self) -> None:
        """
        Initialize the state manager with an empty runtime store.
        """
        self._state: Dict[str, Any] = {}
        logger.debug("Initialized StateManagerAgent with empty state store.")

    def set(self, key: str, value: Any) -> None:
        """
        Store a value in shared state by key.

        Args:
            key: The state key to set.
            value: The value to associate with the key.

        Raises:
            StateManagerAgentError: If the key is not a valid non-empty string.
        """
        self._validate_key(key)
        self._state[key] = value
        logger.info("State set: %s", key)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a value from shared state.

        Args:
            key: The state key to retrieve.
            default: Value to return if the key is missing.

        Returns:
            The stored value or the default if the key does not exist.

        Raises:
            StateManagerAgentError: If the key is not a valid non-empty string.
        """
        self._validate_key(key)
        value = self._state.get(key, default)
        logger.info(
            "State retrieved: %s = %s",
            key,
            value,
        )
        return value

    def exists(self, key: str) -> bool:
        """
        Check whether a state key exists.

        Args:
            key: The state key to check.

        Returns:
            True if the key exists in state, otherwise False.

        Raises:
            StateManagerAgentError: If the key is not a valid non-empty string.
        """
        self._validate_key(key)
        exists = key in self._state
        logger.info("State exists check: %s = %s", key, exists)
        return exists

    def delete(self, key: str) -> None:
        """
        Remove a key and its value from shared state.

        Args:
            key: The state key to delete.

        Raises:
            StateManagerAgentError: If the key is not a valid non-empty string.
        """
        self._validate_key(key)
        if key in self._state:
            del self._state[key]
            logger.info("State deleted: %s", key)
        else:
            logger.info("State delete attempted for missing key: %s", key)

    def clear(self) -> None:
        """
        Clear all runtime shared state.
        """
        self._state.clear()
        logger.info("State cleared.")

    def dump(self) -> Dict[str, Any]:
        """
        Return a shallow copy of the current runtime state.

        Returns:
            A dictionary containing all stored state values.
        """
        state_copy = dict(self._state)
        logger.info("State dump generated with %d entries.", len(state_copy))
        return state_copy

    @staticmethod
    def _validate_key(key: str) -> None:
        """
        Validate that a state key is a non-empty string.

        Args:
            key: The key to validate.

        Raises:
            StateManagerAgentError: If the key is not a valid non-empty string.
        """
        if not isinstance(key, str) or not key.strip():
            logger.error(
                "Invalid state key provided: %r", key
            )
            raise StateManagerAgentError(
                "State key must be a non-empty string."
            )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    state_manager = StateManagerAgent()

    # Store values in shared runtime state.
    state_manager.set("api_url", "https://petstore.swagger.io/v2")
    state_manager.set("timeout", 30)
    state_manager.set("retry_enabled", True)

    # Retrieve individual values.
    api_url = state_manager.get("api_url")
    timeout = state_manager.get("timeout")
    missing_value = state_manager.get("missing_key", default="not found")

    print("Retrieved api_url:", api_url)
    print("Retrieved timeout:", timeout)
    print("Retrieved missing_key with default:", missing_value)

    # Check existence and delete a value.
    print("timeout exists:", state_manager.exists("timeout"))
    state_manager.delete("timeout")
    print("timeout exists after delete:", state_manager.exists("timeout"))

    # Dump the complete state so far.
    print("State dump after delete:", state_manager.dump())

    # Clear all state and verify the store is empty.
    state_manager.clear()
    print("State dump after clear:", state_manager.dump())
