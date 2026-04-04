import logging
from abc import ABC
from dataclasses import dataclass
from typing import Callable
 
logger = logging.getLogger(__name__)
 
 
# --- Operation Metadaten ---
 
@dataclass
class OperationConfig:
    """
    Pflichtangaben die das Framework braucht um eine Operation zu registrieren.
    Wird vom @operation Dekorator befüllt.
    """
    topic: str          # auf welches SubmodelElement-idShort wird gehört
    execute_when: str   # everytime | onlyontrue | onlyonfalse | never
    method_name: str    # wird automatisch vom Dekorator gesetzt (func.__name__)
 
 
@dataclass
class GuardResult:
    """Rückgabe einer Guard-Funktion."""
    proceed: bool
    reason: str = ""
 
 
# --- Dekorator ---
 
def operation(topic: str, execute_when: str = "everytime", guard: str | None = None):
    """
    Registriert eine Methode als Operation für ein bestimmtes Topic.
 
    Pflichtparameter:
        topic:        idShort des SubmodelElements auf das gehört wird
        execute_when: everytime | onlyontrue | onlyonfalse | never
 
    Optionale Parameter:
        guard:        Name einer Methode die vor der Operation ausgeführt wird.
                      Gibt GuardResult zurück — bei proceed=False wird die Operation übersprungen.
 
    Beispiel:
        @operation(topic="emissionfactor", execute_when="everytime")
        def set_emission_factor(self, payload):
            ...
 
        @operation(topic="resetaggregation", execute_when="onlyontrue", guard="check_aggregation_running")
        def reset_aggregation(self, payload):
            ...
 
        def check_aggregation_running(self) -> GuardResult:
            if not self._aggregation_running:
                return GuardResult(proceed=False, reason="Keine Aggregation aktiv")
            return GuardResult(proceed=True)
    """
    def decorator(func: Callable) -> Callable:
        # Metadaten direkt an die Funktion hängen → BaseOperationService liest sie beim Init
        func._operation_config = OperationConfig(
            topic=topic,
            execute_when=execute_when,
            method_name=func.__name__,
        )
        func._operation_guard = guard  # Name der Guard-Methode (oder None)
        return func
    return decorator
 
 
# --- Basis-Klasse ---
 
class BaseOperationService(ABC):
    """
    Basisklasse für alle Operation-Services.
    Liest beim Init automatisch alle mit @operation dekorierten Methoden
    und registriert sie in der internen Registry.
    """
 
    def __init__(self):
        self._registry: dict[str, tuple[OperationConfig, Callable, Callable | None]] = {}
        self._build_registry()
 
    def _build_registry(self) -> None:
        """Durchsucht alle Methoden nach @operation Dekoratoren und registriert sie."""
        for attr_name in dir(self):
            method = getattr(self, attr_name, None)
            if callable(method) and hasattr(method, "_operation_config"):
                config: OperationConfig = method._operation_config
                guard_name: str | None = method._operation_guard
 
                # Guard-Methode auflösen (falls angegeben)
                guard = None
                if guard_name:
                    guard = getattr(self, guard_name, None)
                    if guard is None:
                        raise ValueError(
                            f"Operation '{config.method_name}': "
                            f"Guard-Methode '{guard_name}' nicht gefunden"
                        )
 
                self._registry[config.topic.lower()] = (config, method, guard)
                logger.debug(
                    f"Operation registriert: topic='{config.topic}' "
                    f"method='{config.method_name}' "
                    f"execute_when='{config.execute_when}' "
                    f"guard='{guard_name or 'keiner'}'"
                )
 
        logger.info(f"{self.__class__.__name__}: {len(self._registry)} Operation(en) registriert: "
                    f"{list(self._registry.keys())}")
 
    def get_registry(self) -> dict[str, tuple[OperationConfig, Callable, Callable | None]]:
        """Gibt die Registry zurück — wird vom EventHandler verwendet."""
        return self._registry