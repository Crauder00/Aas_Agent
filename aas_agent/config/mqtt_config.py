"""mqtt_config.py - Configuration dataclass for MQTT settings."""

from dataclasses import dataclass


@dataclass
class MqttConfig:
    """Configuration for MQTT connection settings.

    Attributes:
        host: The MQTT broker host. Defaults to "localhost".
        port: The MQTT broker port. Defaults to 1883.
        topic_filter: The topic filter for MQTT messages. Defaults to a standard filter.
        client_id: The MQTT client ID. Defaults to "aas-agent".
    """
    host: str = "localhost" # standard host
    port: int = 1883 # Standard MQTT-Port
    topic_filter: str = "sm-repository/+/submodels/+/submodelElements/+/updated"  # Standard-Filter
    client_id: str = "aas-agent"
