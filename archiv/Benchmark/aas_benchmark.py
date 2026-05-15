"""
AAS Server Benchmark Script
============================
Misst die Latenz von BaSyx AAS Server Endpoints.

Einfach die Funktion `run_scenario()` anpassen, um andere Endpoints zu testen.
Ergebnisse werden als CSV gespeichert.

Verwendung:
    python aas_benchmark.py
    python aas_benchmark.py --runs 200 --output results/my_test.csv
"""

import time
import csv
import argparse
import statistics
import os
from datetime import datetime
from typing import Callable, Any

from aas_python_http_client import (
    ApiClient,
    Configuration,
    AssetAdministrationShellRepositoryAPIApi,
    SubmodelRepositoryAPIApi,
)

# ============================================================
#  KONFIGURATION – hier anpassen
# ============================================================

HOST = "http://192.168.1.128:8081"
DEFAULT_RUNS = 1000
DEFAULT_WARMUP = 5
OUTPUT_DIR = "benchmark/results"

# ============================================================
#  CLIENT SETUP
# ============================================================

configuration = Configuration()
configuration.host = HOST

api_client = ApiClient(configuration=configuration)
aasRepoClient = AssetAdministrationShellRepositoryAPIApi(api_client=api_client)
smRepoClient = SubmodelRepositoryAPIApi(api_client=api_client)


# ============================================================
#  SZENARIEN – hier den Aufruf austauschen
# ============================================================
#
#  Jedes Szenario ist ein Dict mit:
#    "name"     : Anzeigename für Reports
#    "fn"       : Lambda/Callable ohne Argumente → führt den API-Call durch
#
#  Zum Austauschen einfach "fn" ändern, z.B.:
#    "fn": lambda: aasRepoClient.get_asset_administration_shell_by_id("deine-id")
#

SCENARIOS = [
    {
        "name": "get_all_shells",
        "label": "GET /shells (alle AAS)",
        "fn": lambda: aasRepoClient.get_all_asset_administration_shells(),
    },
    {
        "name": "get_all_submodels",
        "label": "GET /submodels (alle Submodelle)",
        "fn": lambda: smRepoClient.get_all_submodels(),
    },
    # --- Weitere Szenarien hier einfügen ---
    # {
    #     "name": "get_single_shell",
    #     "label": "GET /shells/{id}",
    #     "fn": lambda: aasRepoClient.get_asset_administration_shell_by_id("DEINE_SHELL_ID"),
    # },
    # {
    #     "name": "get_all_submodel_elements",
    #     "label": "GET /submodelElements (alle)",
    #     "fn": lambda: aasRepoClient.get_all_submodel_elements_aas_repository("DEINE_SHELL_ID", "DEIN_SUBMODEL_ID"),
    # },
]


# ============================================================
#  BENCHMARK LOGIK
# ============================================================

def measure_once(fn: Callable) -> dict:
    """Führt einen einzelnen API-Call durch und misst Latenz + Erfolg."""
    start = time.perf_counter()
    error = None
    response_size = None

    try:
        result = fn()
        # Grobe Schätzung der Antwortgröße (Anzahl Elemente wenn Liste)
        if isinstance(result, list):
            response_size = len(result)
        elif hasattr(result, "result"):
            response_size = len(result.result) if result.result else 0
    except Exception as e:
        error = str(e)

    elapsed_ms = (time.perf_counter() - start) * 1000  # → Millisekunden

    return {
        "latency_ms": round(elapsed_ms, 3),
        "success": error is None,
        "error": error or "",
        "response_size": response_size,
    }


def run_benchmark(scenario: dict, runs: int, warmup: int) -> list[dict]:
    """Führt ein Szenario N mal aus, mit Warmup-Phase."""
    fn = scenario["fn"]
    name = scenario["name"]
    label = scenario["label"]

    print(f"\n{'='*60}")
    print(f"  Szenario : {label}")
    print(f"  Warmup   : {warmup} Runs (werden nicht gezählt)")
    print(f"  Messungen: {runs} Runs")
    print(f"{'='*60}")

    # Warmup
    print(f"  [Warmup] ", end="", flush=True)
    for i in range(warmup):
        try:
            fn()
        except Exception:
            pass
        print(".", end="", flush=True)
    print(" fertig")

    # Messung
    results = []
    errors = 0
    print(f"  [Messen] ", end="", flush=True)

    for i in range(runs):
        r = measure_once(fn)
        r["run"] = i + 1
        r["scenario"] = name
        r["label"] = label
        r["timestamp"] = datetime.now().isoformat()
        results.append(r)

        if not r["success"]:
            errors += 1

        # Fortschritt alle 10 Runs
        if (i + 1) % 10 == 0:
            print(f"{i+1}", end="", flush=True)
        else:
            print(".", end="", flush=True)

    print(f" fertig ({errors} Fehler)")
    return results


def print_summary(results: list[dict], scenario: dict):
    """Gibt Statistiken auf der Konsole aus."""
    latencies = [r["latency_ms"] for r in results if r["success"]]
    errors = [r for r in results if not r["success"]]

    if not latencies:
        print("  Alle Requests fehlgeschlagen!")
        return

    print(f"\n  Statistik für: {scenario['label']}")
    print(f"  {'─'*45}")
    print(f"  Erfolgreiche Runs : {len(latencies)} / {len(results)}")
    print(f"  Fehler            : {len(errors)}")
    print(f"  {'─'*45}")
    print(f"  Min               : {min(latencies):.1f} ms")
    print(f"  Max               : {max(latencies):.1f} ms")
    print(f"  Mean (Durchschnitt): {statistics.mean(latencies):.1f} ms")
    print(f"  Median (p50)      : {statistics.median(latencies):.1f} ms")
    print(f"  p95               : {_percentile(latencies, 95):.1f} ms")
    print(f"  p99               : {_percentile(latencies, 99):.1f} ms")
    print(f"  Stddev            : {statistics.stdev(latencies):.1f} ms")
    print(f"  {'─'*45}")

    if errors:
        print(f"\n  Erste Fehlermeldung: {errors[0]['error'][:100]}")


def _percentile(data: list[float], p: int) -> float:
    """Berechnet das p-te Perzentil einer sortierten Liste."""
    sorted_data = sorted(data)
    idx = (len(sorted_data) - 1) * p / 100
    lo = int(idx)
    hi = lo + 1
    if hi >= len(sorted_data):
        return sorted_data[lo]
    frac = idx - lo
    return sorted_data[lo] + frac * (sorted_data[hi] - sorted_data[lo])


# ============================================================
#  CSV EXPORT
# ============================================================

def save_to_csv(all_results: list[dict], filepath: str):
    """Speichert alle Ergebnisse als CSV."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    fieldnames = ["run", "scenario", "label", "timestamp", "latency_ms", "success", "response_size", "error"]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)

    print(f"\n  Ergebnisse gespeichert: {filepath}")
    print(f"     → {len(all_results)} Zeilen")


def save_summary_csv(all_results: list[dict], filepath: str):
    """Speichert eine kompakte Zusammenfassung pro Szenario als CSV."""
    summary_path = filepath.replace(".csv", "_summary.csv")

    # Gruppieren nach Szenario
    by_scenario: dict[str, list[float]] = {}
    for r in all_results:
        if r["success"]:
            by_scenario.setdefault(r["scenario"], []).append(r["latency_ms"])

    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "scenario", "label", "runs", "errors",
            "min_ms", "max_ms", "mean_ms", "median_ms", "p95_ms", "p99_ms", "stddev_ms"
        ])
        writer.writeheader()

        for scenario_name, latencies in by_scenario.items():
            # Label aus results holen
            label = next(r["label"] for r in all_results if r["scenario"] == scenario_name)
            total_runs = sum(1 for r in all_results if r["scenario"] == scenario_name)
            errors = total_runs - len(latencies)

            writer.writerow({
                "scenario": scenario_name,
                "label": label,
                "runs": total_runs,
                "errors": errors,
                "min_ms": round(min(latencies), 1),
                "max_ms": round(max(latencies), 1),
                "mean_ms": round(statistics.mean(latencies), 1),
                "median_ms": round(statistics.median(latencies), 1),
                "p95_ms": round(_percentile(latencies, 95), 1),
                "p99_ms": round(_percentile(latencies, 99), 1),
                "stddev_ms": round(statistics.stdev(latencies) if len(latencies) > 1 else 0, 1),
            })

    print(f" Zusammenfassung gespeichert: {summary_path}")


# ============================================================
#  MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="AAS Server Benchmark")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS, help=f"Anzahl Messungen pro Szenario (default: {DEFAULT_RUNS})")
    parser.add_argument("--warmup", type=int, default=DEFAULT_WARMUP, help=f"Warmup-Runs (default: {DEFAULT_WARMUP})")
    parser.add_argument("--output", type=str, default=None, help="CSV-Ausgabepfad (default: results/benchmark_<timestamp>.csv)")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = args.output or os.path.join(OUTPUT_DIR, f"benchmark_{timestamp}.csv")

    print(f"\n{'='*60}")
    print(f"  AAS Server Benchmark")
    print(f"  Host    : {HOST}")
    print(f"  Runs    : {args.runs} pro Szenario")
    print(f"  Warmup  : {args.warmup} Runs")
    print(f"  Szenarien: {len(SCENARIOS)}")
    print(f"{'='*60}")

    all_results = []

    for scenario in SCENARIOS:
        results = run_benchmark(scenario, runs=args.runs, warmup=args.warmup)
        print_summary(results, scenario)
        all_results.extend(results)

        # Zwischenspeichern nach jedem Szenario (sicher falls Abbruch)
        save_to_csv(all_results, output_path)

    # Abschluss
    save_summary_csv(all_results, output_path)

    print(f"\n{'='*60}")
    print(f"  Benchmark abgeschlossen!")
    print(f"  Rohdaten  : {output_path}")
    print(f"  Summary   : {output_path.replace('.csv', '_summary.csv')}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
