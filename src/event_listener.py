import logging
import paho.mqtt.client as mqtt
from typing import Callable
from .config import MqttConfig

logger = logging.getLogger(__name__)


class EventListener:
    """
    Verbindet sich mit dem MQTT Broker und lauscht auf AAS-Updates.
    Gibt eingehende Nachrichten via Callback weiter — keine Logik hier.
    """

    def __init__(
        self,
        config: MqttConfig,
        on_message: Callable[[str, str], None],
    ):
        self._config = config
        self._on_message = on_message
        self._client = mqtt.Client(client_id=config.client_id)

        # Callbacks registrieren
        self._client.on_connect = self._handle_connect
        self._client.on_message = self._handle_message
        self._client.on_disconnect = self._handle_disconnect

    # ── Öffentliche Methoden ──────────────────────────────

    def start(self) -> None:
        """Verbinden und Loop im Hintergrund-Thread starten."""
        logger.info(f"Verbinde mit MQTT Broker {self._config.host}:{self._config.port}")
        self._client.connect(self._config.host, self._config.port)
        # loop_start() startet einen eigenen Thread — blockiert nicht
        self._client.loop_start()

    def stop(self) -> None:
        """Loop stoppen und Verbindung sauber trennen."""
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("MQTT Verbindung getrennt")

    # ── Private Callbacks (paho-intern) ──────────────────

    def _handle_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            logger.info("MQTT verbunden, abonniere Topics...")
            # client.subscribe(self._config.topic_filter)
            for topic in self._config.topic_filters:
                client.subscribe(topic)
        else:
            logger.error(f"MQTT Verbindung fehlgeschlagen, Code: {rc}")

    def _handle_message(self, client, userdata, message) -> None:
        topic = message.topic
        payload = message.payload.decode("utf-8")
        logger.debug(f"Nachricht empfangen: {topic}")
        # Weiterleiten an den EventHandler — dieser entscheidet was zu tun ist
        self._on_message(topic, payload)

    def _handle_disconnect(self, client, userdata, rc) -> None:
        if rc != 0:
            logger.warning(f"Unerwartete Trennung vom Broker (Code: {rc})")