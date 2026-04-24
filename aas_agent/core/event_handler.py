"""event_handler.py - Event handler for processing MQTT messages and triggering operations."""

# event_handler.py

from concurrent.futures import ThreadPoolExecutor
import json
import logging

from .base_operation_service import BaseOperationService, GuardResult

logger = logging.getLogger(__name__)


class EventHandler:
    """
    Receives topic + payload from EventListener.

    Decides which operation is triggered — based on the generated
    Registry out of the BaseOperationService.
    """

    def __init__(self) -> None:
        """Initialize the EventHandler with empty registry and thread pool."""
        self._registry: dict[str, list] = {}
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._last_values: dict[str, str] = {}  # idShort → letzter Wert

    # ── Öffentliche Methoden ──────────────────────────────

    def handle(self, topic: str, payload: str) -> None:
        """Called by the EventListener.

        Args:
            topic: MQTT topic, e.g. sm-repository/+/submodels/+/submodelElements/{idShort}/updated
            payload: JSON string with AAS update, e.g. {"value": "true"}
        """
        id_short = self._parse_id_short(topic)

        if id_short is None:
            logger.warning(f"Topic could not be parsed: {topic}")
            return

        entries = self._registry.get(id_short.lower())

        if entries is None:
            logger.debug(f"No handler for idShort: '{id_short}' — ignored")
            return

        # execute_when einmal prüfen — gilt für alle Handler dieses idShorts
        # (Wert kommt aus dem Payload, nicht service-spezifisch)
        first_config = entries[0][0]
        if not self._should_execute(first_config.execute_when, payload, id_short):
            logger.debug(f"Skipped operation ({first_config.execute_when})")
            return

        for config, method, guard in entries:
            # Guard pro Service prüfen
            if guard is not None:
                result: GuardResult = guard()
                if not result.proceed:
                    logger.info(
                        f"Operation '{config.method_name}' blocked by guard"
                        + (f": {result.reason}" if result.reason else "")
                    )
                    continue  # nächsten Service prüfen, nicht return!

            logger.info(f"Operation triggered: {config.method_name} (via '{id_short}')")
            self._executor.submit(method, payload)

    def register_service(self, service: BaseOperationService) -> None:
        """Registers a service (several services per idShort possible)."""
        new_entries = service.get_registry()
        for id_short, entry in new_entries.items():
            if id_short not in self._registry:
                self._registry[id_short] = []
            self._registry[id_short].append(entry)
        logger.info(f"Service registered: {type(service).__name__} ({len(new_entries)} Entries)")

    # ── Private Methoden ─────────────────────────────────

    def _parse_id_short(self, topic: str) -> str | None:
        """
        Extracts the idShortPath from the topic.

        Expectes: sm-repository/+/submodels/+/submodelElements/{idShort}/updated
        """
        parts = topic.split("/")
        if len(parts) >= 7 and parts[6] == "updated":
            return parts[5]
        return None

    def _parse_value(self, payload: str) -> str | None:
        """Extracts the value from the AAS JSON payload."""
        try:
            return json.loads(payload).get("value", "").strip().lower()
        except (json.JSONDecodeError, AttributeError):
            logger.warning(f"Payload could not be parsed: {payload}")
            return None

    def _should_execute(self, execute_when: str, payload: str, id_short: str) -> bool:
        """Decides whether to execute the operation based on execute_when."""
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
                logger.warning(f"Unknown execute_when value: '{execute_when}' — skipped")
                return False
