from dataclasses import dataclass, field
from typing import List, Optional

# Mapping von idShort (Kleinbuchstaben) zu Methodenname in AasOperationService
TOPIC_OPERATION_MAP = {
    "emissionfactor":     "set_emission_factor",
    "scope3proxy":        "set_scope3_proxy",
    "resetaggregation":   "reset_aggregation",
    "triggeraggregation": "trigger_aggregation",
}

@dataclass
class MqttConfig:
    host: str = "192.168.1.128"
    port: int = 1883
    # Topic-Pattern vom BaSyx Server
    topic_filter: str = "sm-repository/+/submodels/+/submodelElements/+/updated"
    topic_filters: Optional[List[str]] = None
    client_id: str = "aas-agent"

    # def __post_init__(self):
    #     if self.topic_filters is None:
    #         self.topic_filters = [
    #             "sm-repository/sm-repo/submodels/aHR0cHM6Ly9leGFtcGxlLmNvbS9pZHMvc20vNTY1MF85MTM0XzQ5MzhfNDM0MA/submodelElements/Operations[0]/updated",
    #             "sm-repository/sm-repo/submodels/aHR0cHM6Ly9leGFtcGxlLmNvbS9pZHMvc20vNTY1MF85MTM0XzQ5MzhfNDM0MA/submodelElements/Operations[1]/updated",
    #         ]

@dataclass
class AasSensorConfig:
    sensor_url_sm_repository: str = "http://192.168.1.101:8081"
    # Submodel-ID deines Sensor-Submodels
    sensor_submodel_id: str = "http://example.com/id/sm/..."  
    # idShort des Elements im Sensor-Submodel, z.B. "temperature"
    sensor_submodelelement_id_short: str = "energyvalue"

@dataclass
class AggregationConfig:
    aggregation_interval_seconds: int = 1 # z.B. alle 60 Sekunden aggregieren
    aggregation_max_count: int = 300 # Max Anzahl Werte für Aggregation (z.B. 300 Werte = 5 Minuten (300s) bei 1s Intervall)
    

@dataclass
class AasConfig:
    base_url_sm_repository: str = "http://192.168.1.128:8081"
    # Submodel-IDs
    emission_submodel_id: str = "http://example.com/id/sm/..."
    emission_submodelelement_id_short: str = "emissionfactor"

    scope3_proxy_submodel_id: str = "http://example.com/id/sm/..."
    scope3_proxy_submodelelement_id_short: str = "scope3proxy"

    aggregation_submodel_id: str = "http://example.com/id/sm/..."
    aggregation_submodelelement_id_short: str = "aggregationvalue"

    # Verknüpfung zu anderen Konfigurationen
    sensor: AasSensorConfig = field(default_factory=AasSensorConfig)
    aggregation: AggregationConfig = field(default_factory=AggregationConfig)



@dataclass
class AgentConfig:
    mqtt: MqttConfig = None
    aas: AasConfig = None
    aas_sensor: AasSensorConfig = None

    def __post_init__(self):
        # Defaults setzen falls nichts übergeben wurde
        if self.mqtt is None:
            self.mqtt = MqttConfig()
        if self.aas is None:
            self.aas = AasConfig()
        if self.aas_sensor is None:
            self.aas_sensor = AasSensorConfig()
