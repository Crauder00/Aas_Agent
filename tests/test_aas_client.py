# Define logging configuration
import logging

logging.basicConfig(
    level=logging.WARNING,  # Set to DEBUG for more detailed output
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

from src.aas_client import AASClient

# ── Konfiguration ──────────────────────────────────────────────────────────────
BASE_URL    = "http://192.168.1.128:8081"   # <-- anpassen
SUBMODEL_ID = "https://example.com/ids/sm/5650_9134_4938_4340"      # <-- anpassen
ID_SHORT    = "emissionfactor"            # <-- anpassen
NEW_VALUE   = "0.059"                       # <-- Testwert für PATCH
# ──────────────────────────────────────────────────────────────────────────────

client = AASClient(BASE_URL)

print("=== GET-Wert vor Änderung ===")
value = client.get_value(SUBMODEL_ID, ID_SHORT)
print(f"Gelesener Wert: {value}")

print("=== SET-Wert ===")
success = client.set_value(SUBMODEL_ID, ID_SHORT, NEW_VALUE)
print(f"Wert aktualisiert: {success}")

print("=== GET-Wert nach Änderung ===")
value = client.get_value(SUBMODEL_ID, ID_SHORT)
print(f"Gelesener Wert: {value}")

