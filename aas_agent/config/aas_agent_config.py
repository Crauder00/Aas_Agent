"""aas_agent_config.py - Configuration dataclass for the AasAgent."""

from dataclasses import dataclass, field

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
    """

    mqtt: MqttConfig = field(default_factory=MqttConfig)
    register_config: RegisterConfig | None = None
    listener: ListenerConfig | None = None
