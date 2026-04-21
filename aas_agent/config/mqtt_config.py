# mqtt_config.py 

from dataclasses import dataclass

@dataclass
class MqttConfig:
    host: str = "localhost" # standard host
    port: int = 1883 # Standard MQTT-Port
    topic_filter: str = "sm-repository/+/submodels/+/submodelElements/+/updated"  # Standard-Filter
    client_id: str = "aas-agent"