import logging
from typing import Final

from src.aas_agent import AasAgent
from src.config import AgentConfig, MqttConfig, SubmodelElementConfig
from src.services.emission_service.emission_service_config import EmissionServiceConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

# =============================================================================
# Konstanten
# =============================================================================

LOCAL_AAS: Final[str] = "http://192.168.1.128:8081"
SENSOR_AAS: Final[str] = "http://192.168.1.101:8081"
CF_SUBMODEL_ID: Final[str] = "https://example.com/ids/sm/6218_8934_1526_1612"
SENSOR_SUBMODEL_ID: Final[str] = "https://acplt.org/Simple_Submodel"

# =============================================================================
# Konfiguration
# =============================================================================

agent_config: AgentConfig = AgentConfig(
    mqtt=MqttConfig(
        host="192.168.1.128",
        port=1883,
        client_id="aas-agent",
    ),
)

emission_config: EmissionServiceConfig = EmissionServiceConfig(
    emission_factor=SubmodelElementConfig(LOCAL_AAS, CF_SUBMODEL_ID, "emissionfactor"),
    scope3_proxy=SubmodelElementConfig(LOCAL_AAS, CF_SUBMODEL_ID, "scope3proxy"),
    aggregation_value=SubmodelElementConfig(LOCAL_AAS, CF_SUBMODEL_ID, "aggregationvalue"),
    aggregation_trigger=SubmodelElementConfig(LOCAL_AAS, CF_SUBMODEL_ID, "triggeraggregation"),
    aggregation_reset=SubmodelElementConfig(LOCAL_AAS, CF_SUBMODEL_ID, "resetaggregation"),
    sensor=SubmodelElementConfig(SENSOR_AAS, SENSOR_SUBMODEL_ID, "ExampleProperty"),
)

# =============================================================================
# Start
# =============================================================================

def main() -> None:
    agent = AasAgent(agent_config, emission_config)
    agent.start()

    print("Warte auf MQTT-Nachrichten...")
    input("Drücke Enter zum Beenden...\n")

    agent.stop()


if __name__ == "__main__":
    main()