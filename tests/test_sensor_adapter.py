# Define logging configuration
import logging

logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG for more detailed output
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

from src.sensor_adapter import SensorAdapter
from src.config import AasSensorConfig

# ── Konfiguration ──────────────────────────────────────────────────────────────
SENSOR_BASE_URL = "http://192.168.1.101:8081"   # <-- anpassen
SUBMODEL_ID     = "https://example.com/ids/sm/4339_7297_3282_2812"
ID_SHORT        = "energyvalue"                 # <-- zu testender Sensor
# ──────────────────────────────────────────────────────────────────────────────

config = AasSensorConfig(
    sensor_url_sm_repository=SENSOR_BASE_URL,
    sensor_submodel_id=SUBMODEL_ID,
    sensor_submodelelement_id_short=ID_SHORT,  # Achtung: siehe Kritik unten
)

adapter = SensorAdapter(config)

print("=== GET Sensorwert ===")
value = adapter.get_sensor_reading()
print(f"Gelesener Sensorwert: {value}")