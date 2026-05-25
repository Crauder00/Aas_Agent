import logging
import time

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

from aas_agent import SubmodelRepository

# ── Konfiguration ──────────────────────────────────────────────────────────────
BASE_URL        = "http://192.168.1.149:8081"
SUBMODEL_ID     = "https://zhaw.aas.ch/ids/sm/3365_2132_4062_5551"
ID_SHORTS_TRIGGER = [f"Stations[{i}].triggeraggregation" for i in range(8)]
ID_SHORTS_RESET   = [f"Stations[{i}].resetaggregation"   for i in range(8)]

TOGGLE_INTERVAL_S = 10    # Sekunden zwischen jedem Toggle
TOTAL_DURATION_S  = 220   # Gesamtdauer in Sekunden
# ──────────────────────────────────────────────────────────────────────────────

client = SubmodelRepository(BASE_URL, SUBMODEL_ID)

num_cycles = TOTAL_DURATION_S // TOGGLE_INTERVAL_S
start_time = time.time()

print(f"=== Auto-Toggle gestartet: {num_cycles} Zyklen à {TOGGLE_INTERVAL_S}s "
      f"({TOTAL_DURATION_S}s gesamt) ===\n")

for cycle in range(num_cycles):
    elapsed = time.time() - start_time
    trigger_active = (cycle % 2 == 0)  # Zyklus 0,2,4,... → TRIGGER; 1,3,5,... → RESET

    if trigger_active:
        print(f"[Zyklus {cycle+1:>3}/{num_cycles}] t={elapsed:5.1f}s — TRIGGER (aggregation starten)")
        for id_short in ID_SHORTS_TRIGGER:
            success = client.set_value(id_short, "true")
            print(f"  {id_short}: {'OK' if success else 'FEHLER'}")
    else:
        print(f"[Zyklus {cycle+1:>3}/{num_cycles}] t={elapsed:5.1f}s — RESET  (aggregation zurücksetzen)")
        for id_short in ID_SHORTS_RESET:
            success = client.set_value(id_short, "true")
            print(f"  {id_short}: {'OK' if success else 'FEHLER'}")

    # Warten bis zum nächsten Toggle (ausser nach dem letzten Zyklus)
    if cycle < num_cycles - 1:
        print()
        time.sleep(TOGGLE_INTERVAL_S)

total_elapsed = time.time() - start_time
print(f"\n=== Fertig nach {total_elapsed:.1f}s ===")
