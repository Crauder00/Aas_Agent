from dataclasses import dataclass


# --- Basis-Klassen ---

@dataclass
class SubmodelElementConfig:
    """Referenz auf ein SubmodelElement in irgendeinem AAS-Repository."""
    base_url: str
    submodel_id: str
    id_short: str


# --- MQTT ---

@dataclass
class MqttConfig:
    host: str                                                                       # Pflichtfeld
    port: int = 1883                                                                # Standard MQTT-Port
    topic_filter: str = "sm-repository/+/submodels/+/submodelElements/+/updated"  # Standard-Filter
    client_id: str = "aas-agent"


# --- Top-Level ---

@dataclass
class AgentConfig:
    mqtt: MqttConfig    # Pflichtfeld
