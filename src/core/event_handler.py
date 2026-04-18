import json
import logging
from concurrent.futures import ThreadPoolExecutor
from .base_operation_service import BaseOperationService, OperationConfig, GuardResult

logger = logging.getLogger(__name__)


class EventHandler:
    """
    Empfängt Topic + Payload vom EventListener.
    Entscheidet welche Operation ausgelöst wird — basierend auf der
    Registry des BaseOperationService (nicht mehr TOPIC_OPERATION_MAP).
    """

    def __init__(self):
        self._registry: dict = {}
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._last_values: dict[str, str] = {}  # idShort → letzter Wert

    # ── Öffentliche Methoden ──────────────────────────────

    def handle(self, topic: str, payload: str) -> None:
        """Wird vom EventListener aufgerufen."""
        id_short = self._parse_id_short(topic)

        if id_short is None:
            logger.warning(f"Topic konnte nicht geparst werden: {topic}")
            return

        entry = self._registry.get(id_short.lower())

        if entry is None:
            logger.debug(f"Kein Handler für idShort: '{id_short}' — ignoriert")
            return

        config, method, guard = entry

        # execute_when prüfen
        if not self._should_execute(config.execute_when, payload, id_short):
            logger.debug(f"Operation übersprungen ({config.execute_when}): {config.method_name}")
            return

        # Guard prüfen (falls vorhanden)
        if guard is not None:
            result: GuardResult = guard()
            if not result.proceed:
                logger.info(
                    f"Operation '{config.method_name}' durch Guard blockiert"
                    + (f": {result.reason}" if result.reason else "")
                )
                return

        logger.info(f"Operation ausgelöst: {config.method_name} (via '{id_short}')")
        self._executor.submit(method, payload)

    def register_service(self, service: BaseOperationService) -> None:
        """Registriert einen Service und merged seine Registry."""
        new_entries = service.get_registry()
        conflicts = set(new_entries) & set(self._registry)
        if conflicts:
            logger.warning(f"Registry-Konflikt für idShorts: {conflicts} — werden überschrieben")
        self._registry.update(new_entries)
        logger.info(f"Service registriert: {type(service).__name__} ({len(new_entries)} Einträge)")

    # ── Private Methoden ─────────────────────────────────

    def _parse_id_short(self, topic: str) -> str | None:
        """
        Extrahiert den idShortPath aus dem Topic.
        Erwartet: sm-repository/+/submodels/+/submodelElements/{idShort}/updated
        """
        parts = topic.split("/")
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
        """Entscheidet basierend auf execute_when ob die Operation ausgeführt werden soll."""
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