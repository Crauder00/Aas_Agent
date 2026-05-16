"""
BaSyx AAS Server v2 - Locust Performance Test
==============================================
Szenarien:
  - BrowserUser     : liest alle AAS, dann Shells + Submodels (typischer Browser-User)
  - IoTReaderUser   : liest Submodel-Values und einzelne Elemente in hoher Frequenz

Starten:
  pip install locust

  # Interaktive Web-UI (http://localhost:8089)
  locust -f locustfile.py --host http://localhost:8080

  # Headless / CI - z.B. 50 User, Ramp-up 5 User/s, 2 Minuten
  locust -f locustfile.py --host http://localhost:8080 \
         --headless -u 50 -r 5 --run-time 2m \
         --csv results/basyx --html results/report.html

Umgebungsvariablen (optional):
  BASYX_HOST  - Ziel-URL (überschreibt --host)

Hinweise zum BaSyx v2 API:
  - IDs müssen als Base64url (ohne Padding) in der URL kodiert werden.
  - Verschachtelte idShorts werden mit '.' getrennt, z.B.:
      ProductCarbonFootprintProduction.PcfCO2eq
  - SubmodelElementList-Einträge werden per Index angesprochen, z.B.:
      Stations[0].currentCFSubmodel
  - Der Endpunkt /$value gibt den reinen Wert zurück (kein Modell-Overhead).
  - Der Endpunkt /$metadata gibt Struktur ohne Werte zurück.
"""

import base64
import json
import os
import random
import urllib.request

from locust import HttpUser, TaskSet, between, events, tag, task
from locust.exception import RescheduleTask

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
BASE_PATH = ""  # Leer lassen wenn der Server direkt unter / erreichbar ist

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

# ---------------------------------------------------------------------------
# Globaler State (wird beim Teststart per Discovery befüllt)
# ---------------------------------------------------------------------------

# Liste der bekannten Submodels: [{"id_b64": "...", "elements": ["idShort.path", ...]}, ...]
KNOWN_SUBMODELS: list[dict] = []

# Liste der bekannten AAS-IDs (Base64url-kodiert)
KNOWN_AAS_IDS: list[str] = []


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

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

def get_json_from_server(host: str, path: str) -> dict | None:
    """Führt einen einfachen GET-Request aus und gibt das JSON zurück."""
    url = f"{host}{BASE_PATH}{path}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[Discovery] Fehler beim Abruf von {url}: {e}")
        return None


def extract_element_paths(
    elements: list,
    prefix: str = "",
    parent_is_list: bool = False,
    inside_list_collection: bool = False,
) -> list[str]:
    """
    Extrahiert rekursiv alle BaSyx-v2-kompatiblen Pfade aus SubmodelElements.

    Adressierungsregeln (BaSyx v2 REST API):
    ─────────────────────────────────────────
    • SubmodelElementCollection  →  Kinder per idShort:  parent.childIdShort
    • SubmodelElementList        →  Kinder per Index:    parent[0], parent[1], …
    • Properties ohne idShort    →  nicht adressierbar → werden übersprungen
    • List-in-Collection-in-List (z.B. Stations[0].scope2emissionslist):
      BaSyx kann Stations[0].scope2emissionslist[0] nicht auflösen (→ 404).
      Deshalb wird nur die Liste selbst aufgenommen; /$value liefert alle Werte.

    Parameter:
        parent_is_list         : Eltern-Element ist SubmodelElementList
                                 → dieses Element wird per Index adressiert
        inside_list_collection : Dieses Element liegt in einer Collection,
                                 die selbst Kind einer List ist
                                 → enthaltene Listen sind "List-in-List"
    """
    paths = []

    for i, elem in enumerate(elements):
        model_type = elem.get("modelType", "")
        id_short   = elem.get("idShort", "")

        # ── Pfad-Segment berechnen ──────────────────────────────────────────
        if parent_is_list:
            segment = f"{prefix}[{i}]" if prefix else f"[{i}]"
        else:
            if not id_short:
                continue  # ohne idShort nicht per API adressierbar
            segment = f"{prefix}.{id_short}" if prefix else id_short

        # ── Leaf-Elemente ───────────────────────────────────────────────────
        if model_type in ("Property", "MultiLanguageProperty", "File", "Blob"):
            paths.append(segment)

        # ── SubmodelElementCollection ────────────────────────────────────────
        elif model_type == "SubmodelElementCollection":
            children = elem.get("value") or []
            if isinstance(children, list) and children:
                paths.extend(
                    extract_element_paths(
                        children,
                        prefix=segment,
                        parent_is_list=False,
                        # Wenn diese Collection per Index adressiert wurde
                        # (parent_is_list=True), sind ihre Kinder-Listen
                        # vom Typ "List-in-Collection-in-List"
                        inside_list_collection=parent_is_list,
                    )
                )

        # ── SubmodelElementList ──────────────────────────────────────────────
        elif model_type == "SubmodelElementList":
            children = elem.get("value") or []
            if not isinstance(children, list) or not children:
                continue

            child_type = children[0].get("modelType", "")

            if child_type in ("Property", "MultiLanguageProperty", "File", "Blob"):
                if inside_list_collection:
                    # List-in-Collection-in-List:
                    # z.B. Stations[0].scope2emissionslist
                    # → nur die Liste selbst aufnehmen, nicht die Einzel-Indizes
                    paths.append(segment)
                else:
                    # Normale Liste mit Leaf-Kindern → per Index adressieren
                    for j in range(len(children)):
                        paths.append(f"{segment}[{j}]")

            elif child_type == "SubmodelElementCollection":
                # Liste von Collections (z.B. Stations):
                # Collections per Index, ihre Kinder per idShort
                paths.extend(
                    extract_element_paths(
                        children,
                        prefix=segment,
                        parent_is_list=True,
                        inside_list_collection=False,
                    )
                )
            # List-of-List nicht weiter rekursieren (BaSyx-Limitation)

    return paths


# ---------------------------------------------------------------------------
# Discovery: wird einmalig beim Teststart ausgeführt
# ---------------------------------------------------------------------------

@events.test_start.add_listener
def discover_ids(environment, **kwargs):
    """
    Lädt beim Teststart alle verfügbaren AAS- und Submodel-IDs vom Server
    und extrahiert die Pfade der abfragbaren Elemente pro Submodel.
    """
    host = os.getenv("BASYX_HOST") or environment.host

    # --- AAS-IDs laden ---
    aas_data = get_json_from_server(host, "/shells")
    if aas_data and "result" in aas_data:
        for aas in aas_data["result"][:20]:
            aas_id = aas.get("id")
            if aas_id:
                KNOWN_AAS_IDS.append(b64url(aas_id))
    print(f"[Discovery] AAS gefunden: {len(KNOWN_AAS_IDS)}")

    # --- Submodels laden und Elementpfade extrahieren ---
    sm_data = get_json_from_server(host, "/submodels")
    if sm_data and "result" in sm_data:
        for sm in sm_data["result"][:20]:
            sm_id = sm.get("id")
            if not sm_id:
                continue

            sm_id_b64 = b64url(sm_id)
            elements_raw = sm.get("submodelElements", [])
            element_paths = extract_element_paths(elements_raw)

            if element_paths:
                KNOWN_SUBMODELS.append({
                    "id_b64": sm_id_b64,
                    "id_short": sm.get("idShort", sm_id),
                    "elements": element_paths,
                })
                print(
                    f"[Discovery] Submodel '{sm.get('idShort', sm_id)}': "
                    f"{len(element_paths)} Elemente gefunden"
                )
            else:
                # Submodel ohne extrahierbare Elemente trotzdem registrieren
                KNOWN_SUBMODELS.append({
                    "id_b64": sm_id_b64,
                    "id_short": sm.get("idShort", sm_id),
                    "elements": [],
                })
                print(f"[Discovery] Submodel '{sm.get('idShort', sm_id)}': keine Elemente")

    print(f"[Discovery] Submodels total: {len(KNOWN_SUBMODELS)}")


# ---------------------------------------------------------------------------
# Hilfsmixin
# ---------------------------------------------------------------------------

class BaSyxMixin:
    """Gemeinsame Hilfsmethoden für alle User-Klassen."""

    def api(self, path: str) -> str:
        return f"{BASE_PATH}{path}"

    def random_aas_id(self) -> str:
        if not KNOWN_AAS_IDS:
            raise RescheduleTask()
        return random.choice(KNOWN_AAS_IDS)

    def random_submodel(self) -> dict:
        if not KNOWN_SUBMODELS:
            raise RescheduleTask()
        return random.choice(KNOWN_SUBMODELS)

    def random_submodel_with_elements(self) -> dict:
        """Gibt ein Submodel zurück, das mindestens ein bekanntes Element hat."""
        candidates = [sm for sm in KNOWN_SUBMODELS if sm["elements"]]
        if not candidates:
            raise RescheduleTask()
        return random.choice(candidates)


# ---------------------------------------------------------------------------
# Szenario 1: Browser-User
# Liest AAS-Übersichten, Shell-Details und Submodel-Strukturen
# ---------------------------------------------------------------------------

class BrowserTasks(BaSyxMixin, TaskSet):
    """
    Simuliert einen menschlichen Benutzer, der im AAS-Browser navigiert:
    - Lädt die AAS-Liste
    - Öffnet einzelne Shells
    - Navigiert zu Submodels und liest deren Metadata
    """

    @tag("browser", "list")
    @task(3)
    def list_all_shells(self):
        """Lädt die komplette AAS-Übersichtsliste."""
        self.client.get(
            self.api("/shells"),
            headers=HEADERS,
            name="GET /shells",
        )

    @tag("browser", "list")
    @task(2)
    def list_all_submodels(self):
        """Lädt die komplette Submodel-Übersichtsliste."""
        self.client.get(
            self.api("/submodels"),
            headers=HEADERS,
            name="GET /submodels",
        )

    @tag("browser", "detail")
    @task(4)
    def get_shell_detail(self):
        """Öffnet eine einzelne AAS (Shell-Detail)."""
        aas_id = self.random_aas_id()
        self.client.get(
            self.api(f"/shells/{aas_id}"),
            headers=HEADERS,
            name="GET /shells/{aasId}",
        )

    @tag("browser", "detail")
    @task(5)
    def get_submodel_metadata(self):
        """Liest die Struktur (Metadata) eines Submodels - ohne Werte."""
        sm = self.random_submodel()
        self.client.get(
            self.api(f"/submodels/{sm['id_b64']}/$metadata"),
            headers=HEADERS,
            name="GET /submodels/{smId}/$metadata",
        )

    @tag("browser", "detail")
    @task(3)
    def get_submodel_full(self):
        """
        Liest ein vollständiges Submodel inklusive aller Werte.
        Entspricht dem Öffnen eines Submodels im Browser.
        """
        sm = self.random_submodel()
        self.client.get(
            self.api(f"/submodels/{sm['id_b64']}"),
            headers=HEADERS,
            name="GET /submodels/{smId}",
        )

    @tag("browser", "list")
    @task(2)
    def list_submodel_elements(self):
        """Listet alle SubmodelElements eines Submodels auf (Übersicht)."""
        sm = self.random_submodel()
        self.client.get(
            self.api(f"/submodels/{sm['id_b64']}/submodel-elements"),
            headers=HEADERS,
            name="GET /submodels/{smId}/submodel-elements",
        )


class BrowserUser(BaSyxMixin, HttpUser):
    """Browser-User: navigiert die AAS-Struktur wie ein menschlicher Benutzer.

    fixed_count=1 stellt sicher, dass immer mindestens 1 BrowserUser läuft,
    unabhängig von der Gesamtzahl der User. Die restlichen User werden als
    IoTReaderUser gespawnt. fixed_count hat Vorrang vor weight.
    """
    tasks = [BrowserTasks]
    wait_time = between(1.0, 4.0)  # Menschliche Lesezeit zwischen Requests
    fixed_count = 5


# ---------------------------------------------------------------------------
# Szenario 2: IoT Reader
# Liest Submodel-Values und einzelne Elemente mit hoher Frequenz
# ---------------------------------------------------------------------------

class IoTReaderTasks(BaSyxMixin, TaskSet):
    """
    Simuliert einen IoT-Client oder Dashboard, der in kurzen Intervallen
    Messwerte aus einem Submodel ausliest.
    """

    # Wird beim Start einer Session auf ein konkretes Submodel festgelegt
    pinned_sm: dict = {}

    def on_start(self):
        """Wählt beim Start ein Submodel aus und merkt sich dieses."""
        candidates = [sm for sm in KNOWN_SUBMODELS if sm["elements"]]
        if candidates:
            self.pinned_sm = random.choice(candidates)
        elif KNOWN_SUBMODELS:
            self.pinned_sm = random.choice(KNOWN_SUBMODELS)

    # @tag("iot", "value")
    # @task(6)
    # def get_submodel_value(self):
    #     """Liest alle Werte eines Submodels auf einmal (/$value)."""
    #     if not self.pinned_sm:
    #         raise RescheduleTask()
    #     self.client.get(
    #         self.api(f"/submodels/{self.pinned_sm['id_b64']}/$value"),
    #         headers=HEADERS,
    #         name="GET /submodels/{smId}/$value",
    #     )

    @tag("iot", "element")
    @task(8)
    def get_single_element_value(self):
        """
        Liest den Wert eines einzelnen Elements per /$value.

        Der idShort-Pfad wird aus der Discovery übernommen und entspricht
        der BaSyx v2 Konvention (Punkt-Notation für Verschachtelung,
        eckige Klammern für Listen-Indizes).
        """
        sm = self.pinned_sm
        if not sm or not sm.get("elements"):
            raise RescheduleTask()

        element_path = random.choice(sm["elements"])
        self.client.get(
            self.api(f"/submodels/{sm['id_b64']}/submodel-elements/{encode_element_path(element_path)}/$value"),
            headers=HEADERS,
            name="GET /submodels/{smId}/submodel-elements/{path}/$value",
        )

    @tag("iot", "metadata")
    @task(4)
    def get_submodel_metadata(self):
        """
        Liest periodisch die Metadata eines Submodels.
        Nützlich um Strukturänderungen zu erkennen.
        """
        if not self.pinned_sm:
            raise RescheduleTask()
        self.client.get(
            self.api(f"/submodels/{self.pinned_sm['id_b64']}/$metadata"),
            headers=HEADERS,
            name="GET /submodels/{smId}/$metadata",
        )

    @tag("iot", "switch")
    @task(2)
    def switch_submodel(self):
        """
        Wechselt gelegentlich auf ein anderes Submodel.
        Simuliert einen Client, der zwischen Datenpunkten rotiert.
        """
        candidates = [sm for sm in KNOWN_SUBMODELS if sm["elements"]]
        if candidates:
            self.pinned_sm = random.choice(candidates)


class IoTReaderUser(BaSyxMixin, HttpUser):
    """IoT Reader: liest Werte in hoher Frequenz aus einem gepinnten Submodel.

    Erhält alle User-Slots, die nicht durch fixed_count reserviert sind.
    Bei 10 Users: 5x BrowserUser (fixed), 5x IoTReaderUser.
    """
    tasks = [IoTReaderTasks]
    wait_time = between(0.1, 0.8)  # Schnelle Polling-Rate
