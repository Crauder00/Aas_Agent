"""aas_agent_config.py - Configuration dataclass for the AasAgent."""

from dataclasses import dataclass, field
from typing import Literal

from .listener_config import ListenerConfig
from .mqtt_config import MqttConfig
from .registration_service_config import RegisterConfig


# --- Top-Level ---
@dataclass
class AgentConfig:
    """Top-level configuration for the AasAgent.

    Attributes:
        mqtt: Legacy MQTT settings, used when listener is None.
        listener: MQTT or polling configuration with explicit submodel watches.
        register_config: Optional registration settings. If None, registration is disabled.
        event_mode: Set to disabled for timer-only operation without MQTT or polling.
    """

    mqtt: MqttConfig = field(default_factory=MqttConfig)
    register_config: RegisterConfig | None = None
    listener: ListenerConfig | None = None
    event_mode: Literal["enabled", "disabled"] = "enabled"

    def __post_init__(self) -> None:
        """Validate explicit event-source selection."""
        if self.event_mode not in {"enabled", "disabled"}:
            raise ValueError("event_mode must be 'enabled' or 'disabled'")
