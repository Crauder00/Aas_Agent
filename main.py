"""main.py - Entry point for the AAS agent.

Configures and starts an AAS agent with eight EmissionServices
(Station 0 through 7), using MQTT or polling and sensor data
from the monitoring submodel to calculate the carbon footprint
and write it in the AAS.

Stop: Ctrl+C or `systemctl stop <service>`
"""

import logging
import signal
import threading
import types
from typing import Final

from aas_agent import (
    AasAgent,
    AgentConfig,
    AggregationConfig,
    EmissionService,
    EmissionServiceConfig,
    ListenerConfig,
    SubmodelElementConfig,
    SubmodelWatch,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

# =============================================================================
# Constants
# =============================================================================

MQTT_HOST: Final[str] = "localhost"
EVENT_MODE: Final = "mqtt"  # Change to "polling" to run without an MQTT broker.
POLL_INTERVAL_SECONDS: Final[float] = 1.0

LOCAL_AAS: Final[str] = "http://localhost:8082"
"""Base URL of the local AAS instance (edge device)."""

Product_AAS: Final[str] = "http://localhost:8082"
"""URL of the product AAA instance where the carbon footprint will be written."""

SENSOR_AAS: Final[str] = "http://localhost:8082"
"""URL of the AAS instance that provides the sensor data."""

CF_SUBMODEL_ID: Final[str] = "https://zhaw.aas.ch/ids/sm/3365_2132_4062_5551"
"""Submodel ID for the carbon footprint submodel."""

SENSOR_SUBMODEL_ID: Final[str] = "http://example.com/submodel/monitoring"
"""Submodel ID for the sensor monitoring submodel."""

# =============================================================================
# Configuration of the agent and services
# =============================================================================

emission_config_station_0: EmissionServiceConfig = EmissionServiceConfig(
    base_url=LOCAL_AAS,
    product_url=Product_AAS,
    submodel_id=CF_SUBMODEL_ID,
    sensor=SubmodelElementConfig(SENSOR_AAS, SENSOR_SUBMODEL_ID, "sensorvalue0"),
    station_index=0,
    aggregation=AggregationConfig(0.1, 3000),
)
"""EmissionService configuration for station 0 (reads `sensorvalue0`)."""

emission_config_station_1: EmissionServiceConfig = EmissionServiceConfig(
    base_url=LOCAL_AAS,
    product_url=Product_AAS,
    submodel_id=CF_SUBMODEL_ID,
    sensor=SubmodelElementConfig(SENSOR_AAS, SENSOR_SUBMODEL_ID, "sensorvalue1"),
    station_index=1,
    aggregation=AggregationConfig(0.1, 3000),
)
"""EmissionService configuration for station 1 (reads `sensorvalue1`)."""

emission_config_station_2: EmissionServiceConfig = EmissionServiceConfig(
    base_url=LOCAL_AAS,
    product_url=Product_AAS,
    submodel_id=CF_SUBMODEL_ID,
    sensor=SubmodelElementConfig(SENSOR_AAS, SENSOR_SUBMODEL_ID, "sensorvalue2"),
    station_index=2,
    aggregation=AggregationConfig(0.1, 3000),
)
"""EmissionService configuration for station 2 (reads `sensorvalue2`)."""

emission_config_station_3: EmissionServiceConfig = EmissionServiceConfig(
    base_url=LOCAL_AAS,
    product_url=Product_AAS,
    submodel_id=CF_SUBMODEL_ID,
    sensor=SubmodelElementConfig(SENSOR_AAS, SENSOR_SUBMODEL_ID, "sensorvalue3"),
    station_index=3,
    aggregation=AggregationConfig(0.1, 3000),
)
"""EmissionService configuration for station 3 (reads `sensorvalue3`)."""

emission_config_station_4: EmissionServiceConfig = EmissionServiceConfig(
    base_url=LOCAL_AAS,
    product_url=Product_AAS,
    submodel_id=CF_SUBMODEL_ID,
    sensor=SubmodelElementConfig(SENSOR_AAS, SENSOR_SUBMODEL_ID, "sensorvalue4"),
    station_index=4,
    aggregation=AggregationConfig(0.1, 3000),
)
"""EmissionService configuration for station 4 (reads `sensorvalue4`)."""

emission_config_station_5: EmissionServiceConfig = EmissionServiceConfig(
    base_url=LOCAL_AAS,
    product_url=Product_AAS,
    submodel_id=CF_SUBMODEL_ID,
    sensor=SubmodelElementConfig(SENSOR_AAS, SENSOR_SUBMODEL_ID, "sensorvalue5"),
    station_index=5,
    aggregation=AggregationConfig(0.1, 3000),
)
"""EmissionService configuration for station 5 (reads `sensorvalue5`)."""

emission_config_station_6: EmissionServiceConfig = EmissionServiceConfig(
    base_url=LOCAL_AAS,
    product_url=Product_AAS,
    submodel_id=CF_SUBMODEL_ID,
    sensor=SubmodelElementConfig(SENSOR_AAS, SENSOR_SUBMODEL_ID, "sensorvalue6"),
    station_index=6,
    aggregation=AggregationConfig(0.1, 3000),
)
"""EmissionService configuration for station 6 (reads `sensorvalue6`)."""

emission_config_station_7: EmissionServiceConfig = EmissionServiceConfig(
    base_url=LOCAL_AAS,
    product_url=Product_AAS,
    submodel_id=CF_SUBMODEL_ID,
    sensor=SubmodelElementConfig(SENSOR_AAS, SENSOR_SUBMODEL_ID, "sensorvalue7"),
    station_index=7,
    aggregation=AggregationConfig(0.1, 3000),
)
"""EmissionService configuration for station 7 (reads `sensorvalue7`)."""


# =============================================================================
# Start
# =============================================================================


def main() -> None:
    """Start the AAS agent and waits for a stop signal.

    Process:
        1. Register signal handlers for SIGTERM and SIGINT (Ctrl+C).
        2. Creates eight EmissionServices (Station 0 through 7).
        3. Starts the AasAgent with these services.
        4. Blocks until a stop signal is received.
        5. Shuts down the agent cleanly.
    """
    stop_event = threading.Event()

    def handle_signal(sig: int, frame: types.FrameType | None) -> None:
        """Set the stop event when SIGTERM or SIGINT is received."""
        logging.info("Signal received, shutting down...")
        stop_event.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    services = [
        EmissionService(emission_config_station_0),
        EmissionService(emission_config_station_1),
        EmissionService(emission_config_station_2),
        EmissionService(emission_config_station_3),
        EmissionService(emission_config_station_4),
        EmissionService(emission_config_station_5),
        EmissionService(emission_config_station_6),
        EmissionService(emission_config_station_7),
    ]

    # Reuse the exact service instances registered with AasAgent.
    # Add another SubmodelWatch for each additional repository/submodel.
    agent_config = AgentConfig(
        listener=ListenerConfig(
            mode=EVENT_MODE,
            host=MQTT_HOST,
            poll_interval_seconds=POLL_INTERVAL_SECONDS,
            watches=[
                SubmodelWatch(
                    base_url=LOCAL_AAS,
                    submodel_id=CF_SUBMODEL_ID,
                    services=services,
                ),
            ],
        ),
    )

    agent = AasAgent(agent_config, services)
    agent.start()
    print(f"Agent running in {EVENT_MODE} mode...")

    stop_event.wait()
    agent.stop()


if __name__ == "__main__":
    main()
