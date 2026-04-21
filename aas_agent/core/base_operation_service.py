# base_operation_service.py

import logging
from abc import ABC
from dataclasses import dataclass
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class OperationConfig:
    topic:        str
    execute_when: str
    method_name:  str


@dataclass
class GuardResult:
    proceed: bool
    reason:  str = ""


class BaseOperationService(ABC):
    """
    Basisklasse für alle Operation-Services.
    Subklassen rufen self.register() in ihrem __init__ auf
    um Methoden für Topics anzumelden.
    """

    def __init__(self):
        self._registry: dict[str, tuple[OperationConfig, Callable, Callable | None]] = {}

    def register(
        self,
        method:       Callable,
        topic:        str,
        execute_when: str = "everytime",
        guard:        Callable | None = None,
    ) -> None:
        """
        Registriert eine Methode für ein Topic.

        Args:
            method:       Gebundene Methode des Service (z.B. self.set_emission_factor)
            topic:        idShort des SubmodelElements (aus Config)
            execute_when: everytime | onlyontrue | onlyonfalse | never
            guard:        Optionale Guard-Methode die GuardResult zurückgibt
        """
        config = OperationConfig(
            topic=topic,
            execute_when=execute_when,
            method_name=method.__name__,
        )
        key = topic.lower()

        if key in self._registry:
            logger.warning(
                f"{self.__class__.__name__}: Topic '{topic}' wird überschrieben "
                f"(war: '{self._registry[key][0].method_name}')"
            )

        self._registry[key] = (config, method, guard)
        logger.debug(
            f"Operation registriert: topic='{topic}' "
            f"method='{method.__name__}' "
            f"execute_when='{execute_when}' "
            f"guard='{guard.__name__ if guard else 'keiner'}'"
        )

    def get_registry(self) -> dict[str, tuple[OperationConfig, Callable, Callable | None]]:
        """Gibt die Registry zurück — wird vom EventHandler verwendet."""
        return self._registry

    def _log_registry_summary(self) -> None:
        logger.info(
            f"{self.__class__.__name__}: {len(self._registry)} Operation(en) registriert: "
            f"{list(self._registry.keys())}"
        )