"""base_operation_service.py - Base class for all operation services."""

from collections.abc import Callable
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class OperationConfig:
    """Holds the registration metadata for a single operation.

    Attributes:
        topic: The idShort of the SubmodelElement this operation listens to.
        execute_when: Execution condition - one of: everytime | onlyontrue | onlyonfalse | never.
        method_name: Name of the bound method, used for logging.
    """
    topic:        str
    execute_when: str
    method_name:  str


@dataclass
class GuardResult:
    """
    Return type of a guard function, indicating whether an operation should proceed.

    Attributes:
        proceed: If True, the operation is executed.
        reason: Optional explanation, used for logging when proceed is False.
    """
    proceed: bool
    reason:  str = ""


class BaseOperationService:
    """
    Abstract base class for all operation services.

    Subclasses call self.register() in their __init__ to bind methods to topics.
    """

    def __init__(self) -> None:
        """Initialize the operation registry."""
        self._registry: dict[str, tuple[OperationConfig, Callable, Callable | None]] = {}


    def register(
        self,
        method:       Callable,
        topic:        str,
        execute_when: str = "everytime",
        guard:        Callable | None = None,
    ) -> None:
        """
        Register a method for a given topic.

        Args:
            method: Bound method of the service (e.g. self.set_emission_factor).
            topic: idShort of the SubmodelElement (from config).
            execute_when: Execution condition - everytime | onlyontrue | onlyonfalse | never.
            guard: Optional guard function returning a GuardResult.
        """
        config = OperationConfig(
            topic=topic,
            execute_when=execute_when,
            method_name=method.__name__,
        )
        key = topic.lower()

        if key in self._registry:
            logger.warning(
                f"{self.__class__.__name__}: Topic '{topic}' is being overwritten "
                f"(previous: '{self._registry[key][0].method_name}')"
            )

        self._registry[key] = (config, method, guard)
        logger.debug(
            f"Operation registered: topic='{topic}' "
            f"method='{method.__name__}' "
            f"execute_when='{execute_when}' "
            f"guard='{guard.__name__ if guard else 'none'}'"
        )

    def get_registry(self) -> dict[str, tuple[OperationConfig, Callable, Callable | None]]:
        """Return the operation registry - used by the EventHandler to resolve incoming topics."""
        return self._registry

    def _log_registry_summary(self) -> None:
        """Log a summary of all registered operations for this service."""
        logger.info(
            f"{self.__class__.__name__}: {len(self._registry)} Operation(s) registered: "
            f"{list(self._registry.keys())}"
        )
