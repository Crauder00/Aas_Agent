import signal
import threading
import logging
from typing import Final

from src.aas_agent import AasAgent
from src.aas_agent_config import AgentConfig
from src.services.emission_service.emission_service import EmissionService
from src.services.emission_service.emission_service_config import EmissionServiceConfig, AggregationConfig, SubmodelElementConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

# =============================================================================
# Konstanten
# =============================================================================

LOCAL_AAS: Final[str] = "http://localhost:8081"
SENSOR_AAS: Final[str] = "http://192.168.1.101:8081"
CF_SUBMODEL_ID: Final[str] = "http://example.com/submodel/carbonfootprint"
SENSOR_SUBMODEL_ID: Final[str] = "http://example.com/submodel/carbonfootprint"

# =============================================================================
# Konfiguration des Agent und der Services
# =============================================================================

agent_config: AgentConfig = AgentConfig(
    # register_config=RegisterConfig(
        # mainserver_url="http://<HAUPT_SERVER>:8081"), #optional falls 
)


emission_config_station_0: EmissionServiceConfig = EmissionServiceConfig(
    base_url      = LOCAL_AAS,
    product_url   = LOCAL_AAS,
    submodel_id   = CF_SUBMODEL_ID,
    sensor        = SubmodelElementConfig(SENSOR_AAS, SENSOR_SUBMODEL_ID, "totalemissions"),
    station_index = 0,
    aggregation   = AggregationConfig(0.1, 3000)
)


# =============================================================================
# Start
# =============================================================================

def main() -> None:
    stop_event = threading.Event()

    def handle_signal(sig, frame):
        logging.info("Signal empfangen, beende...")
        stop_event.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # ── Start Agent ─────────────────────────────────────────────────────── 
    services = [
        EmissionService(emission_config_station_0)
    ]

    agent = AasAgent(agent_config, services)
    agent.start()
    print("Warte auf MQTT-Nachrichten...")

    # ── End Agent ───────────────────────────────────────────────────────
    stop_event.wait()  # blockiert bis Ctrl+C oder systemctl stop
    agent.stop()

if __name__ == "__main__":
    main()