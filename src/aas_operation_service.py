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

    def set_emission_factor(self) -> None:
        logger.info("[STUB] set_emission_factor() aufgerufen")
        print("  → set_emission_factor(): würde Wert vom AAS Server lesen und setzen")

    def set_scope3_proxy(self) -> None:
        logger.info("[STUB] set_scope3_proxy() aufgerufen")
        print("  → set_scope3_proxy(): würde Scope3-Proxy Wert aktualisieren")

    def reset_aggregation(self) -> None:
        logger.info("[STUB] reset_aggregation() aufgerufen")
        print("  → reset_aggregation(): würde laufende Aggregation abbrechen")

    def trigger_aggregation(self, stop_event: threading.Event) -> None:
        logger.info("[STUB] trigger_aggregation() aufgerufen")
        print("  → trigger_aggregation(): würde Aggregation starten (~1 min)")
        # Simuliert einen langen Lauf — prüft alle 5s ob abgebrochen werden soll
        for i in range(12):
            if stop_event.wait(timeout=5):
                print("  → trigger_aggregation(): abgebrochen via stop_event")
                return
            print(f"  → trigger_aggregation(): läuft... ({(i+1)*5}s)")
        print("  → trigger_aggregation(): abgeschlossen")