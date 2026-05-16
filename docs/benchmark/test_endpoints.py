"""
BaSyx AAS Server v2 - Endpoint Tester
======================================
Testet systematisch alle GET-Endpunkte, die das Locust-Skript verwendet,
und zeigt genau welche Pfade funktionieren und welche nicht.

Starten:
    python test_endpoints.py --host http://localhost:8080

Optionen:
    --host      Ziel-URL des BaSyx-Servers       (default: http://localhost:8080)
    --only-fail Nur fehlgeschlagene Requests zeigen
    --json      Zusätzlich einen JSON-Report speichern (test_report.json)
    --timeout   Request-Timeout in Sekunden       (default: 10)
"""

import argparse
import base64
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime

# ── ANSI-Farben (werden deaktiviert wenn kein TTY) ──────────────────────────
USE_COLOR = sys.stdout.isatty()

def c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text

OK    = lambda t: c("32", t)   # grün
FAIL  = lambda t: c("31", t)   # rot
WARN  = lambda t: c("33", t)   # gelb
BOLD  = lambda t: c("1",  t)   # fett
DIM   = lambda t: c("2",  t)   # grau


# ── Datenklassen ─────────────────────────────────────────────────────────────

@dataclass
class TestResult:
    category: str       # z.B. "Shell", "Submodel/$value", "Element/$value"
    url: str
    status: int         # HTTP-Statuscode, 0 = Netzwerkfehler
    duration_ms: float
    error: str = ""     # Fehlermeldung falls status != 2xx

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


@dataclass
class Report:
    host: str
    started_at: str
    results: list[TestResult] = field(default_factory=list)

    def add(self, result: TestResult):
        self.results.append(result)

    @property
    def passed(self) -> list[TestResult]:
        return [r for r in self.results if r.ok]

    @property
    def failed(self) -> list[TestResult]:
        return [r for r in self.results if not r.ok]


# ── Hilfsfunktionen (identisch mit locustfile.py) ────────────────────────────

def b64url(value: str) -> str:
    """Kodiert eine ID nach Base64url (ohne Padding) für URL-Pfade."""
    return base64.urlsafe_b64encode(value.encode()).rstrip(b"=").decode()


def encode_element_path(path: str) -> str:
    """
    Percent-encodiert eckige Klammern in SubmodelElement-Pfaden.
    BaSyx v2 erwartet:  Stations%5B0%5D.currentCFSubmodel
    statt:              Stations[0].currentCFSubmodel
    """
    return path.replace("[", "%5B").replace("]", "%5D")

def extract_element_paths(
    elements: list,
    prefix: str = "",
    parent_is_list: bool = False,
    inside_list_collection: bool = False,
) -> list[str]:
    """
    Extrahiert rekursiv alle BaSyx-v2-kompatiblen Pfade aus SubmodelElements.
    Identische Logik wie im locustfile.py.
    """
    paths = []

    for i, elem in enumerate(elements):
        model_type = elem.get("modelType", "")
        id_short   = elem.get("idShort", "")

        if parent_is_list:
            segment = f"{prefix}[{i}]" if prefix else f"[{i}]"
        else:
            if not id_short:
                continue
            segment = f"{prefix}.{id_short}" if prefix else id_short

        if model_type in ("Property", "MultiLanguageProperty", "File", "Blob"):
            paths.append(segment)

        elif model_type == "SubmodelElementCollection":
            children = elem.get("value") or []
            if isinstance(children, list) and children:
                paths.extend(
                    extract_element_paths(
                        children,
                        prefix=segment,
                        parent_is_list=False,
                        inside_list_collection=parent_is_list,
                    )
                )

        elif model_type == "SubmodelElementList":
            children = elem.get("value") or []
            if not isinstance(children, list) or not children:
                continue

            child_type = children[0].get("modelType", "")

            if child_type in ("Property", "MultiLanguageProperty", "File", "Blob"):
                if inside_list_collection:
                    paths.append(segment)
                else:
                    for j in range(len(children)):
                        paths.append(f"{segment}[{j}]")

            elif child_type == "SubmodelElementCollection":
                paths.extend(
                    extract_element_paths(
                        children,
                        prefix=segment,
                        parent_is_list=True,
                        inside_list_collection=False,
                    )
                )

    return paths


# ── HTTP-Client ───────────────────────────────────────────────────────────────

def get(host: str, path: str, timeout: int) -> TestResult:
    """Führt einen GET-Request aus und gibt ein TestResult zurück."""
    url = f"{host}{path}"
    category = _categorize(path)
    t0 = time.monotonic()
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()  # Body vollständig lesen
            duration_ms = (time.monotonic() - t0) * 1000
            return TestResult(category, url, resp.status, duration_ms)
    except urllib.error.HTTPError as e:
        duration_ms = (time.monotonic() - t0) * 1000
        body = ""
        try:
            body = e.read().decode(errors="replace")[:200]
        except Exception:
            pass
        return TestResult(category, url, e.code, duration_ms, error=body)
    except Exception as e:
        duration_ms = (time.monotonic() - t0) * 1000
        return TestResult(category, url, 0, duration_ms, error=str(e))


def _categorize(path: str) -> str:
    if path.endswith("/$value") and "submodel-elements" in path:
        return "Element /$value"
    if path.endswith("/$metadata"):
        return "Submodel /$metadata"
    if path.endswith("/$value"):
        return "Submodel /$value"
    if "submodel-elements" in path:
        return "Element (kein $value)"
    if "/submodels/" in path:
        return "Submodel (full)"
    if "/shells/" in path:
        return "Shell"
    if path == "/shells":
        return "Shell Liste"
    if path == "/submodels":
        return "Submodel Liste"
    return "Sonstige"


# ── Discovery ─────────────────────────────────────────────────────────────────

def discover(host: str, timeout: int) -> tuple[list[dict], list[str]]:
    """
    Lädt alle Submodels und AAS vom Server und extrahiert Pfade.
    Gibt (submodels, aas_ids) zurück.
    """
    submodels = []
    aas_ids   = []

    # AAS-Liste
    try:
        req = urllib.request.Request(
            f"{host}/shells", headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
        for aas in data.get("result", []):
            if aas_id := aas.get("id"):
                aas_ids.append(b64url(aas_id))
    except Exception as e:
        print(WARN(f"[Discovery] Konnte AAS-Liste nicht laden: {e}"))

    # Submodel-Liste
    try:
        req = urllib.request.Request(
            f"{host}/submodels", headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
        for sm in data.get("result", []):
            sm_id = sm.get("id")
            if not sm_id:
                continue
            sm_id_b64  = b64url(sm_id)
            id_short   = sm.get("idShort", sm_id)
            elements   = sm.get("submodelElements", [])
            elem_paths = extract_element_paths(elements)
            submodels.append({
                "id":      sm_id,
                "id_b64":  sm_id_b64,
                "idShort": id_short,
                "elements": elem_paths,
            })
            print(f"  Submodel '{id_short}': {len(elem_paths)} Elemente gefunden")
    except Exception as e:
        print(WARN(f"[Discovery] Konnte Submodel-Liste nicht laden: {e}"))

    return submodels, aas_ids


# ── Test-Suites ───────────────────────────────────────────────────────────────

def build_test_urls(
    host: str,
    submodels: list[dict],
    aas_ids: list[str],
) -> list[tuple[str, str]]:
    """
    Erstellt alle zu testenden (category, path)-Paare.
    """
    tests: list[tuple[str, str]] = []

    # Listen-Endpunkte
    tests.append(("Shell Liste",    "/shells"))
    tests.append(("Submodel Liste", "/submodels"))

    # Shell-Endpunkte
    for aas_id in aas_ids:
        tests.append(("Shell", f"/shells/{aas_id}"))

    # Submodel-Endpunkte
    for sm in submodels:
        smid = sm["id_b64"]
        tests.append(("Submodel (full)",    f"/submodels/{smid}"))
        tests.append(("Submodel /$metadata", f"/submodels/{smid}/$metadata"))
        tests.append(("Submodel /$value",    f"/submodels/{smid}/$value"))
        tests.append(("Element Liste",       f"/submodels/{smid}/submodel-elements"))

        # Element-Endpunkte
        for path in sm["elements"]:
            tests.append((
                "Element /$value",
                f"/submodels/{smid}/submodel-elements/{encode_element_path(path)}/$value",
            ))

    return tests


# ── Output ────────────────────────────────────────────────────────────────────

def print_result(result: TestResult, only_fail: bool):
    if only_fail and result.ok:
        return

    status_str = OK(f"HTTP {result.status}") if result.ok else FAIL(f"HTTP {result.status}")
    dur_str    = DIM(f"{result.duration_ms:6.0f}ms")

    # URL kürzen für Lesbarkeit
    display_url = result.url
    if len(display_url) > 100:
        display_url = display_url[:97] + "…"

    print(f"  {status_str}  {dur_str}  {display_url}")
    if result.error:
        # Fehler-Body eingerückt ausgeben
        for line in result.error.splitlines()[:3]:
            print(f"             {FAIL(line)}")


def print_summary(report: Report, only_fail: bool):
    total  = len(report.results)
    passed = len(report.passed)
    failed = len(report.failed)

    print()
    print(BOLD("═" * 70))
    print(BOLD("  ZUSAMMENFASSUNG"))
    print(BOLD("═" * 70))
    print(f"  Gesamt:        {total}")
    print(f"  {OK('Erfolgreich:')}    {passed}")
    if failed:
        print(f"  {FAIL('Fehlgeschlagen:')} {failed}")

    # Fehler nach Kategorie gruppieren
    if failed:
        print()
        print(BOLD("  Fehler nach Kategorie:"))
        by_cat: dict[str, list[TestResult]] = {}
        for r in report.failed:
            by_cat.setdefault(r.category, []).append(r)
        for cat, results in sorted(by_cat.items()):
            print(f"    {FAIL('✗')} {cat}: {len(results)} Fehler")
            for r in results[:3]:  # max. 3 Beispiele pro Kategorie
                short = r.url.split("/submodel-elements/")[-1] if "submodel-elements" in r.url else r.url
                print(f"        {DIM(short)}  →  HTTP {r.status}")
            if len(results) > 3:
                print(f"        {DIM(f'... und {len(results)-3} weitere')}")

    # Durchschnittliche Antwortzeiten
    print()
    print(BOLD("  Antwortzeiten (Ø ms) nach Kategorie:"))
    by_cat_all: dict[str, list[float]] = {}
    for r in report.results:
        by_cat_all.setdefault(r.category, []).append(r.duration_ms)
    for cat, durations in sorted(by_cat_all.items()):
        avg = sum(durations) / len(durations)
        print(f"    {cat:<30} Ø {avg:6.0f} ms  (n={len(durations)})")

    print(BOLD("═" * 70))
    print(f"  Gestartet: {report.started_at}")
    print(f"  Server:    {report.host}")
    print()


def save_json_report(report: Report, path: str = "test_report.json"):
    data = {
        "host": report.host,
        "started_at": report.started_at,
        "summary": {
            "total":  len(report.results),
            "passed": len(report.passed),
            "failed": len(report.failed),
        },
        "results": [
            {
                "category":    r.category,
                "url":         r.url,
                "status":      r.status,
                "ok":          r.ok,
                "duration_ms": round(r.duration_ms, 1),
                "error":       r.error,
            }
            for r in report.results
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  JSON-Report gespeichert: {path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Testet alle GET-Endpunkte des BaSyx AAS Servers."
    )
    parser.add_argument("--host",      default="http://localhost:8080",
                        help="BaSyx-Server URL (default: http://localhost:8080)")
    parser.add_argument("--only-fail", action="store_true",
                        help="Nur fehlgeschlagene Requests anzeigen")
    parser.add_argument("--json",      action="store_true",
                        help="Zusätzlich einen JSON-Report als test_report.json speichern")
    parser.add_argument("--timeout",   type=int, default=10,
                        help="Request-Timeout in Sekunden (default: 10)")
    args = parser.parse_args()

    host = args.host.rstrip("/")
    report = Report(host=host, started_at=datetime.now().isoformat(timespec="seconds"))

    # ── Discovery ─────────────────────────────────────────────────────────
    print(BOLD(f"\n BaSyx Endpoint Tester"))
    print(BOLD(f" Server: {host}\n"))
    print(BOLD("── Discovery ────────────────────────────────────────────────────────"))
    submodels, aas_ids = discover(host, args.timeout)
    print(f"  AAS gefunden:      {len(aas_ids)}")
    print(f"  Submodels gefunden: {len(submodels)}")
    total_elements = sum(len(sm["elements"]) for sm in submodels)
    print(f"  Element-Pfade:     {total_elements}")

    if not submodels and not aas_ids:
        print(FAIL("\n Keine Daten gefunden - Server erreichbar?"))
        sys.exit(1)

    # ── Tests bauen ────────────────────────────────────────────────────────
    tests = build_test_urls(host, submodels, aas_ids)
    print(f"\n{BOLD('── Tests ────────────────────────────────────────────────────────────')}")
    print(f"  {len(tests)} Endpunkte werden getestet …\n")

    # ── Tests ausführen ────────────────────────────────────────────────────
    current_category = ""
    for category, path in tests:
        # Kategorie-Header ausgeben wenn neue Kategorie beginnt
        if category != current_category:
            current_category = category
            print(BOLD(f"\n  [{category}]"))

        result = get(host, path, args.timeout)
        report.add(result)
        print_result(result, args.only_fail)

    # ── Zusammenfassung ────────────────────────────────────────────────────
    print_summary(report, args.only_fail)

    if args.json:
        save_json_report(report)

    # Exit-Code: 1 wenn es Fehler gab
    sys.exit(0 if not report.failed else 1)


if __name__ == "__main__":
    main()
