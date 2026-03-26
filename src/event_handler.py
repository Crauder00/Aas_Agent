import logging
from concurrent.futures import ThreadPoolExecutor
import threading
from .aas_operation_service import AasOperationService
from .config import TOPIC_OPERATION_MAP # Mapping: idShortPath → Methodenname im AasOperationService

logger = logging.getLogger(__name__)

class EventHandler:
    """
    Empfängt Topic + Payload vom EventListener.
    Entscheidet welche Operation ausgelöst wird.
    Langläufer (Aggregation) laufen in einem eigenen Thread.
    """

    def __init__(self, operation_service: AasOperationService):
        self._service = operation_service
        self._operation_map = TOPIC_OPERATION_MAP
        self._executor = ThreadPoolExecutor(max_workers=2) # Max 2 gleichzeitige Operationen — genug für schwache Hardware
        self._stop_aggregation = threading.Event() # Event um laufende Aggregation von aussen stoppen zu können

    # ── Öffentliche Methoden ──────────────────────────────

    def handle(self, topic: str, payload: str) -> None:
        """Einstiegspunkt — wird vom EventListener aufgerufen."""
        id_short = self._parse_id_short(topic)
        if id_short is None:
            logger.warning(f"Topic konnte nicht geparst werden: {topic}")
            return

        operation_name = self._operation_map.get(id_short.lower())
        if operation_name is None:
            logger.debug(f"Kein Handler für idShort: '{id_short}' — ignoriert")
            return

        logger.info(f"Operation ausgelöst: {operation_name} (via {id_short})")
        self._dispatch(operation_name)

    # ── Private Methoden ─────────────────────────────────

    def _parse_id_short(self, topic: str) -> str | None:
        """
        Extrahiert den idShortPath aus dem Topic.
        Erwartet: sm-repository/+/submodels/+/submodelElements/{idShort}/updated
        """
        parts = topic.split("/")
        # Index 5 = idShortPath, Index 6 = "updated"
        if len(parts) >= 7 and parts[6] == "updated":
            return parts[5]
        return None

    def _dispatch(self, operation_name: str) -> None:
        """Schickt die Operation in den ThreadPool."""
        if operation_name == "trigger_aggregation":
            # Altes Stop-Event zurücksetzen bevor neuer Lauf startet
            self._stop_aggregation.clear()
            self._executor.submit(
                self._service.trigger_aggregation,
                self._stop_aggregation,
            )
        elif operation_name == "reset_aggregation":
            # Stop-Signal an laufende Aggregation senden
            self._stop_aggregation.set()
            self._executor.submit(self._service.reset_aggregation)
        else:
            # Alle anderen Operationen: direkt in Thread-Pool
            method = getattr(self._service, operation_name)
            self._executor.submit(method)