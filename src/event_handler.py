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
    """

    def __init__(self, operation_service: AasOperationService):
        self._service = operation_service
        self._operation_map = TOPIC_OPERATION_MAP
        self._executor = ThreadPoolExecutor(max_workers=2) # Max 2 gleichzeitige Operationen — genug für schwache Hardware

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
        method = getattr(self._service, operation_name)
        self._executor.submit(method) 