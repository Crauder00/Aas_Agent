from dataclasses import dataclass
from typing import List, Optional

@dataclass
class MqttConfig:
    host: str = "192.168.1.128"
    port: int = 1883
    # Topic-Pattern vom BaSyx Server
    # topic_filter: str = "sm-repository/sm-repo/submodels/aHR0cHM6Ly9leGFtcGxlLmNvbS9pZHMvc20vNTY1MF85MTM0XzQ5MzhfNDM0MA/submodelElements/Operations[0]/updated"
    topic_filters: Optional[List[str]] = None
    client_id: str = "aas-agent"

    def __post_init__(self):
        if self.topic_filters is None:
            self.topic_filters = [
                "sm-repository/sm-repo/submodels/aHR0cHM6Ly9leGFtcGxlLmNvbS9pZHMvc20vNTY1MF85MTM0XzQ5MzhfNDM0MA/submodelElements/Operations[0]/updated",
                "sm-repository/sm-repo/submodels/aHR0cHM6Ly9leGFtcGxlLmNvbS9pZHMvc20vNTY1MF85MTM0XzQ5MzhfNDM0MA/submodelElements/Operations[1]/updated",
            ]


@dataclass
class AasConfig:
    base_url: str = "http://192.168.1.128:8080"
    # Submodel-ID deines Emission-Submodels (Base64URL-encoded)
    emission_submodel_id: str = "your-submodel-id-base64"


@dataclass
class AgentConfig:
    mqtt: MqttConfig = None
    aas: AasConfig = None

    def __post_init__(self):
        # Defaults setzen falls nichts übergeben wurde
        if self.mqtt is None:
            self.mqtt = MqttConfig()
        if self.aas is None:
            self.aas = AasConfig()