from dataclasses import dataclass, field
from typing import Optional

from src.services.registration_service.registration_service_config import RegisterConfig


# --- MQTT ---
@dataclass
class MqttConfig:
    host: str = "localhost" # standard host
    port: int = 1883 # Standard MQTT-Port
    topic_filter: str = "sm-repository/+/submodels/+/submodelElements/+/updated"  # Standard-Filter
    client_id: str = "aas-agent"


# --- Top-Level ---
@dataclass
class AgentConfig:
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    register_config: Optional[RegisterConfig] = None
