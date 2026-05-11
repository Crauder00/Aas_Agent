"""event_listener.py - Event listener for MQTT-based AAS updates."""

from collections.abc import Callable
import logging

import paho.mqtt.client as mqtt

from ..config.mqtt_config import MqttConfig

logger = logging.getLogger(__name__)


class EventListener:
    """
    Connects to the MQTT broker and listens for AAS updates.

    Passes incoming messages via callback — no logic here.
    """

    def __init__(
        self,
        config: MqttConfig,
        on_message: Callable[[str, str], None],
    ) -> None:
        """Initialize the EventListener with MQTT configuration and message callback."""
        self._config = config
        self._on_message = on_message
        self._client = mqtt.Client(client_id=config.client_id)

        # Callbacks registrieren
        self._client.on_connect = self._handle_connect
        self._client.on_message = self._handle_message
        self._client.on_disconnect = self._handle_disconnect

    # ── Public methods ──────────────────────────────

    def start(self) -> None:
        """Connect and start loop in background thread."""
        logger.info(f"Verbinde mit MQTT Broker {self._config.host}:{self._config.port}")
        self._client.connect(self._config.host, self._config.port)
        # loop_start() startet einen eigenen Thread — blockiert nicht
        self._client.loop_start()

    def stop(self) -> None:
        """Stop the loop and disconnect cleanly."""
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("MQTT connection disconnected")

    # ── Private Callbacks (paho-intern) ──────────────────

    def _handle_connect(self, client: mqtt.Client, userdata: object, flags: dict, rc: int) -> None:
        if rc == 0:
            logger.info("MQTT connected, subscribe to Topics...")
            client.subscribe(self._config.topic_filter)
        else:
            logger.error(f"MQTT connection failed, code: {rc}")

    def _handle_message(self, client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
        topic = message.topic
        payload = message.payload.decode("utf-8")
        logger.debug(f"Message received: {topic}")
        # Weiterleiten an den EventHandler — dieser entscheidet was zu tun ist
        self._on_message(topic, payload)

    def _handle_disconnect(self, client: mqtt.Client, userdata: object, rc: int) -> None:
        if rc != 0:
            logger.warning(f"Unexpected disconnection from broker (code: {rc})")
