from dataclasses import dataclass


@dataclass
class MqttConfig:
    host: str = "localhost"
    port: int = 1883
    # Topic-Pattern vom BaSyx Server
    topic_filter: str = "sm-repository/+/submodels/+/submodelElements/+/updated"
    client_id: str = "aas-agent"


@dataclass
class AasConfig:
    base_url: str = "http://localhost:8080"
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