import json
import logging
from concurrent.futures import ThreadPoolExecutor
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
        self._executor = ThreadPoolExecutor(max_workers=2) # Max 2 gleichzeitige Threads für Operationen
        self._last_values: dict[str, str] = {}  # idShort → letzter Wert

    # ── Öffentliche Methoden ──────────────────────────────

    def handle(self, topic: str, payload: str) -> None:
        """wird vom EventListener aufgerufen."""
        id_short = self._parse_id_short(topic) # Extrahiere idShort aus Topic

        # Wenn idShort nicht extrahiert werden konnte, ignorieren
        if id_short is None:
            logger.warning(f"Topic konnte nicht geparst werden: {topic}")
            return
        
        operation_name = self._operation_map.get(id_short.lower()) # Finde zugehörige Operation basierend auf idShort

        # Wenn kein Handler für den idShort existiert, ignorieren
        if operation_name is None:
            logger.debug(f"Kein Handler für idShort: '{id_short}' — ignoriert")
            return

        # Entscheiden ob Operation ausgeführt werden soll basierend auf execute_when parameter in TOPIC_OPERATION_MAP
        if not self._should_execute(operation_name.execute_when, payload, id_short):
            logger.debug(f"Operation übersprungen ({operation_name.execute_when}): {operation_name.method}")
            return
        
        logger.info(f"Operation ausgelöst: {operation_name.method} (via {id_short})")
        self._dispatch(operation_name.method) # Operation asynchron im ThreadPool ausführen

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
    
    def _parse_value(self, payload: str) -> str | None:
        """Extrahiert den Wert aus dem AAS JSON-Payload."""
        try:
            return json.loads(payload).get("value", "").strip().lower()
        except (json.JSONDecodeError, AttributeError):
            logger.warning(f"Payload konnte nicht geparst werden: {payload}")
            return None
        
    def _should_execute(self, execute_when: str, payload: str, id_short: str) -> bool:
        '''Entscheidet basierend auf execute_when, ob die Operation ausgeführt werden soll.'''
        match execute_when:
            case "everytime":
                return True
            case "never":
                return False
            case "onlyontrue" | "onlyonfalse":
                value = self._parse_value(payload)
                if value is None:
                    return False
    
                last = self._last_values.get(id_short)
                self._last_values[id_short] = value
    
                if execute_when == "onlyontrue":
                    return value == "true" and last != "true"
                else:
                    return value == "false" and last != "false"
            case _:
                logger.warning(f"Unbekannter execute_when-Wert: '{execute_when}' — übersprungen")
                return False
            
    def _dispatch(self, operation_name: str) -> None:
        method = getattr(self._service, operation_name)
        self._executor.submit(method) 