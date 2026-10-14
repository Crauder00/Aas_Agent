"""Event sources for MQTT updates and periodic reconciliation."""

from collections.abc import Callable
from dataclasses import dataclass, field
import logging
import threading

import paho.mqtt.client as mqtt

from ..config.mqtt_config import MqttConfig
from .event_handler import SubmodelWatch

logger = logging.getLogger(__name__)


@dataclass
class ListenerConfig(MqttConfig):
    """Optional reconciliation settings; existing MqttConfig remains supported.

    watches explicitly bind repositories/submodels to registered service instances.
    topic_filter may be a string or a list of MQTT filters (Java and Go together).
    Future event sources can call EventHandler.request_refresh directly.
    """

    mode: str = "mqtt"
    poll_interval_seconds: float = 1.0
    watches: list[SubmodelWatch] = field(default_factory=list)
    topic_filter: str | list[str] = "basyx/submodelrepository/submodel/updated"


class EventListener:
    """Owns source lifecycle; business decisions remain in EventHandler."""

    def __init__(
        self, config: MqttConfig, on_message: Callable[[str, str], None]
    ) -> None:
        """Configure a source and optional explicit submodel watches."""
        self._config = config
        self._on_message = on_message
        self._mode = getattr(config, "mode", "mqtt")
        self._interval = getattr(config, "poll_interval_seconds", 1.0)
        if self._mode not in {"mqtt", "polling"}:
            raise ValueError("Listener mode must be 'mqtt' or 'polling'")
        if self._interval <= 0:
            raise ValueError("poll_interval_seconds must be positive")
        # AasAgent already passes the bound EventHandler.handle callback.
        # Plain callbacks remain supported for the original MQTT-only interface.
        self._handler = getattr(on_message, "__self__", None)
        watches = getattr(config, "watches", [])
        if watches or self._mode == "polling":
            if not watches:
                raise ValueError("Polling requires at least one SubmodelWatch")
            if not callable(getattr(self._handler, "configure_watches", None)):
                raise ValueError(
                    "Reconciliation requires an EventHandler.handle callback"
                )
            self._handler.configure_watches(watches)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started = False
        self._client = None
        if self._mode == "mqtt":
            self._client = mqtt.Client(client_id=config.client_id)
            self._client.on_connect = self._handle_connect
            self._client.on_message = self._handle_message
            self._client.on_disconnect = self._handle_disconnect

    def start(self) -> None:
        """Load the baseline before starting either event source."""
        if self._started:
            return
        if callable(getattr(self._handler, "initialize_watches", None)):
            self._handler.initialize_watches()
        self._stop.clear()
        if self._mode == "polling":
            self._thread = threading.Thread(
                target=self._poll, name="aas-polling", daemon=True
            )
            self._thread.start()
        else:
            self._client.connect(self._config.host, self._config.port)
            self._client.loop_start()
        self._started = True

    def stop(self) -> None:
        """Stop the source and finish already submitted handler work."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
        if self._client is not None and self._started:
            self._client.disconnect()
            self._client.loop_stop()
        if callable(getattr(self._handler, "close", None)):
            self._handler.close()
        self._started = False

    def _poll(self) -> None:
        while not self._stop.wait(self._interval):
            self._handler.request_refresh()

    def _handle_connect(
        self, client: mqtt.Client, userdata: object, flags: dict, rc: int
    ) -> None:
        if rc == 0:
            filters = self._config.topic_filter
            client.subscribe(
                [(topic, 0) for topic in filters]
                if isinstance(filters, list)
                else filters
            )
            # Also reconcile changes missed during a disconnect.
            if callable(getattr(self._handler, "request_refresh", None)):
                self._handler.request_refresh()
        else:
            logger.error("MQTT connection failed, code: %s", rc)

    def _handle_message(
        self, client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage
    ) -> None:
        try:
            self._on_message(message.topic, message.payload.decode("utf-8"))
        except UnicodeDecodeError, ValueError, TypeError:
            logger.exception("Invalid MQTT message on %s", message.topic)

    def _handle_disconnect(
        self, client: mqtt.Client, userdata: object, rc: int
    ) -> None:
        if rc != 0:
            logger.warning("Unexpected broker disconnection (code: %s)", rc)
