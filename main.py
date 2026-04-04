import logging
from src.config import AgentConfig, MqttConfig, SubmodelElementConfig
from src.services.emission_service.emission_service_config import EmissionServiceConfig, AggregationConfig
from src.services.emission_service.emission_service import EmissionService
from src.core.event_listener import EventListener
from src.core.event_handler import EventHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S"
)

# =============================================================================
# Konstanten
# =============================================================================

LOCAL_AAS = "http://192.168.1.128:8081"
SENSOR_AAS = "http://192.168.1.101:8081"
CF_SUBMODEL_ID = "https://example.com/ids/sm/6218_8934_1526_1612"
SENSOR_SUBMODEL_ID = "https://acplt.org/Simple_Submodel"

# =============================================================================
# Konfiguration
# =============================================================================

config = AgentConfig(
    mqtt=MqttConfig(
        host="192.168.1.128",
        port=1883,
        client_id="aas-agent",
    ),
)

scope2_config = EmissionServiceConfig(
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

service = EmissionService(scope2_config)
handler = EventHandler(service)
listener = EventListener(config.mqtt, on_message=handler.handle)
listener.start()

print("Warte auf MQTT-Nachrichten...")
input("Drücke Enter zum Beenden...\n")
listener.stop()
