# aas_agent_config.py

from dataclasses import dataclass, field
from typing import Optional

from .mqtt_config import MqttConfig
from .registration_service_config import RegisterConfig


# --- Top-Level ---
@dataclass
class AgentConfig:
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    register_config: Optional[RegisterConfig] = None
    
