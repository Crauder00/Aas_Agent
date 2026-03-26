import logging
import threading
from .config import AasConfig

logger = logging.getLogger(__name__)


class AasOperationService:
    """
    Enthält die eigentlichen Operationen des AAS Agents.
    Aktuell: Stubs mit Print-Ausgabe.
    Später: echte Logik via SensorAdapter.
    """

    def __init__(self, config: AasConfig):
        self._config = config
        self._stop_aggregation = threading.Event()

    def set_emission_factor(self) -> None:
        logger.info("[STUB] set_emission_factor() aufgerufen")
        print("  → set_emission_factor(): würde Wert vom AAS Server lesen und setzen")

    def set_scope3_proxy(self) -> None:
        logger.info("[STUB] set_scope3_proxy() aufgerufen")
        print("  → set_scope3_proxy(): würde Scope3-Proxy Wert aktualisieren")

    def trigger_aggregation(self) -> None:
        self._stop_aggregation.clear()             
        # ... Aggregationslogik ...
        for i in range(12):
            if self._stop_aggregation.wait(timeout=5):
                print("  → abgebrochen")
                return
            print(f"  → läuft... ({(i+1)*5}s)")

    def reset_aggregation(self) -> None:
        self._stop_aggregation.set()              
        print("  → reset_aggregation(): Aggregation gestoppt")