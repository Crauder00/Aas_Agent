# Define logging configuration
import logging

logging.basicConfig(
    level=logging.WARNING,  # Set to DEBUG for more detailed output
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

# from src.utils.aas_sm_http_client import AasSmHttpClient
from aas_agent.core.utils.submodel_repository import SubmodelRepository as AasSmHttpClient

# ── Konfiguration ──────────────────────────────────────────────────────────────
BASE_URL    = "http://192.168.1.101:8081"   # <-- anpassen
SUBMODEL_ID = "http://example.com/submodel/carbonfootprint"      # <-- anpassen
ID_SHORT    = "ProductCarbonFootprints[0].PcfCO2eq"            # <-- anpassen
NEW_VALUE   = 0.059                       # <-- Testwert für PATCH
# ──────────────────────────────────────────────────────────────────────────────

client = AasSmHttpClient(BASE_URL, SUBMODEL_ID)

print("=== GET-Wert vor Änderung ===")
# value = client.get_value(ID_SHORT)
value = client.get_value_list("scope2emissions6list")
print(f"Gelesener Wert: {value}")

# print("=== SET-Wert ===")
# success = client.set_value(ID_SHORT, NEW_VALUE)
# print(f"Wert aktualisiert: {success}")

# print("=== GET-Wert nach Änderung ===")
# value = client.get_value(ID_SHORT)
# print(f"Gelesener Wert: {value}")

