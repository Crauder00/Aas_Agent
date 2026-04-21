# Define logging configuration
import logging

logging.basicConfig(
    level=logging.WARNING,  # Set to DEBUG for more detailed output
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

from aas_agent.utils.aas_sm_http_client import AasSmHttpClient

# ── Konfiguration ──────────────────────────────────────────────────────────────
BASE_URL    = "http://192.168.1.128:8081"   # <-- anpassen
SUBMODEL_ID = "https://example.com/ids/sm/6218_8934_1526_1612"      # <-- anpassen
ID_SHORT    = "emissionfactor"            # <-- anpassen
NEW_VALUE   = 0.059                       # <-- Testwert für PATCH
# ──────────────────────────────────────────────────────────────────────────────

client = AasSmHttpClient(BASE_URL)

print("=== GET-Wert vor Änderung ===")
value = client.get_value(SUBMODEL_ID, ID_SHORT)
print(f"Gelesener Wert: {value}")

print("=== SET-Wert ===")
success = client.set_value(SUBMODEL_ID, ID_SHORT, NEW_VALUE)
print(f"Wert aktualisiert: {success}")

print("=== GET-Wert nach Änderung ===")
value = client.get_value(SUBMODEL_ID, ID_SHORT)
print(f"Gelesener Wert: {value}")

