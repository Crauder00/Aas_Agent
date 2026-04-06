# Define logging configuration
import logging
import random

logging.basicConfig(
    level=logging.WARNING,  # Set to DEBUG for more detailed output
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

from src.core.utils.aas_sm_http_client import AasSmHttpClient
import time

# ── Konfiguration ──────────────────────────────────────────────────────────────
BASE_URL    = "http://192.168.1.101:8081"   # <-- anpassen
SUBMODEL_ID = "http://example.com/submodel/carbonfootprint"      # <-- anpassen
ID_SHORT    = "totalemissions"            # <-- anpassen
# ──────────────────────────────────────────────────────────────────────────────

client = AasSmHttpClient(BASE_URL)

try:
    while True:
        value = client.get_value(SUBMODEL_ID, ID_SHORT)
        print(f"ausgelesener Wert : {value}")
        value = random.uniform(0.0, 1.0)  # Generiere einen zufälligen Wert zwischen 0.0 und 1.0
        print(f"generierter Wert  : {value}")
        ok = client.set_value(SUBMODEL_ID, ID_SHORT, value)
        time.sleep(2)
except KeyboardInterrupt:
    print("\nStopped by user")
