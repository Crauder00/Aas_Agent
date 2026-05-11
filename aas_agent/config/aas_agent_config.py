"""aas_agent_config.py - Configuration dataclass for the AasAgent."""

from dataclasses import dataclass, field

from .mqtt_config import MqttConfig
from .registration_service_config import RegisterConfig


# --- Top-Level ---
@dataclass
class AgentConfig:
    """Top-level configuration for the AasAgent.

    Attributes:
        mqtt: MQTT connection settings. Defaults to a default MqttConfig instance.
        register_config: Optional registration settings. If None, registration is disabled.
    """
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    register_config: RegisterConfig | None = None

