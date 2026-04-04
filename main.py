import logging
from src.config import (
    AgentConfig,
    MqttConfig,
    AasConfig,
    AggregationConfig,
    SubmodelElementConfig,
    SensorConfig,
)
from src.scope2_emission_service import Scope2EmissionService
from src.event_listener import EventListener
from src.event_handler import EventHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S"
)

# =============================================================================
# Konfiguration
# =============================================================================

CF_SUBMODEL_ID = "https://example.com/ids/sm/6218_8934_1526_1612"

config = AgentConfig(
    mqtt=MqttConfig(
        host="192.168.1.128",
        port=1883,
        client_id="aas-agent",
    ),
    aas=AasConfig(
        base_url="http://192.168.1.128:8081",
        emission_factor=SubmodelElementConfig(
            submodel_id=CF_SUBMODEL_ID,
            id_short="emissionfactor",
        ),
        scope3_proxy=SubmodelElementConfig(
            submodel_id=CF_SUBMODEL_ID,
            id_short="scope3proxy",
        ),
        aggregation_value=SubmodelElementConfig(
            submodel_id=CF_SUBMODEL_ID,
            id_short="aggregationvalue",
        ),
        aggregation_trigger=SubmodelElementConfig(
            submodel_id=CF_SUBMODEL_ID,
            id_short="triggeraggregation",
        ),
        aggregation_reset=SubmodelElementConfig(
            submodel_id=CF_SUBMODEL_ID,
            id_short="resetaggregation",
        ),
        sensor=SensorConfig(
            base_url="http://192.168.1.101:8081",
            submodel_id="https://acplt.org/Simple_Submodel",
            id_short="ExampleProperty",
        ),
        aggregation=AggregationConfig(
            aggregation_interval_seconds=1,
            aggregation_max_count=300,
        ),
    ),
)

# =============================================================================
# Start
# =============================================================================

service = Scope2EmissionService(config.aas)
handler = EventHandler(service)
listener = EventListener(config.mqtt, on_message=handler.handle)
listener.start()

print("Warte auf MQTT-Nachrichten...")
input("Drücke Enter zum Beenden...\n")
listener.stop()