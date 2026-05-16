# Define logging configuration
import logging

logging.basicConfig(
    level=logging.WARNING,  # Set to DEBUG for more detailed output
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

from aas_agent import SubmodelRepository

# ── Konfiguration ──────────────────────────────────────────────────────────────
BASE_URL    = "http://192.168.1.128:8081"   # <-- anpassen
SUBMODEL_ID = "https://zhaw.aas.ch/ids/sm/3365_2132_4062_5551"      # <-- anpassen
ID_SHORTS_TRIGGER   = [f"Stations[{i}].triggeraggregation" for i in range(8)]  # Stations[0]..Stations[7]
ID_SHORTS_RESET   = [f"Stations[{i}].resetaggregation" for i in range(8)]  # Stations[0]..Stations[7]
# ──────────────────────────────────────────────────────────────────────────────

client = SubmodelRepository(BASE_URL, SUBMODEL_ID)

TRIGGER = False

if TRIGGER:
    print("=== Start aggregation (trigger) ===")
    for id_short in ID_SHORTS_TRIGGER:
        success = client.set_value(id_short, "true")
        print(f"Wert aktualisiert: {success}")
else:
    print("=== Reset aggregation (reset) ===")
    for id_short in ID_SHORTS_RESET:
        success = client.set_value(id_short, "true")
        print(f"Wert aktualisiert: {success}")

