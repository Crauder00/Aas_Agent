import logging
import threading
from .config import AasConfig, AasSensorConfig
from .aas_sm_http_client import AasSmHttpClient
from .sensor_adapter import SensorAdapter

logger = logging.getLogger(__name__)


class AasOperationService:
    """
    Enthält die Operationen des AAS Agents und verwaltet
    den lokalen Zustand (emission_factor, laufende Aggregation).
    """

    def __init__(self, config: AasConfig):
        self._config = config
     

        # ── Lokale Zustände / Variablen ───────────────────────────────────
        
        self._stop_aggregation = threading.Event() # Flag zum Stoppen einer laufenden Aggregation

        self._emission_factor: float | None = None # Zuletzt gelesener Emissionsfaktor   
        self._scope3_proxy: float | None = None # Zuletzt gelesener Scope3-Proxy
        self._aggregation_value: float | None = None # Aktueller Wert der Aggregation
        self._total_emission: float | None = None # Beispiel für aggregierten Emissionswert

        # ── Locks ───────────────────────────────────────────────
        self._emission_factor_lock = threading.Lock() # nicht gleichzeitig auf _emission_factor zugreifen
        self._scope3_proxy_lock = threading.Lock() # nicht gleichzeitig auf _scope3_proxy zugreifen

        # ── AAS Client ─────────────────────────────────────────────
        self._aas_client = AasSmHttpClient(self._config.base_url_sm_repository) # Client für Maschinen-AAS
        
        # ── Sensor Adapter ─────────────────────────────────────────────
        self._sensor_aas_client = SensorAdapter(self._config.sensor) # Client für Sensor-AAS

        # ── Initialisierung ─────────────────────────────────────────────
        self._update_all() # Initiale Werte laden

    # ── Öffentliche Operationen ───────────────────────────

    def set_emission_factor(self) -> None:
        """
        Liest den aktuellen Emissionsfaktor vom AAS Server
        und speichert ihn lokal für die Aggregation.
        """
        logger.info(f"Emissionsfaktor vor aktualisierung: {self._emission_factor}")

        raw = self._aas_client.get_value(
            self._config.emission_submodel_id,
            self._config.emission_submodelelement_id_short,
        )

        if raw is None:
            logger.error("set_emission_factor(): Wert konnte nicht gelesen werden")
            return

        try:
            new_value = float(raw)
        except ValueError:
            logger.error(f"set_emission_factor(): Ungültiger Wert '{raw}'")
            return

        # Lock: sicherstellen dass trigger_aggregation() gerade
        # nicht gleichzeitig liest während wir schreiben
        with self._emission_factor_lock:
            self._emission_factor = new_value

        logger.info(f"Emissionsfaktor aktualisiert: {self._emission_factor}")

    def trigger_aggregation(self) -> None:
        """
        Startet die Aggregation. Läuft bis stop_aggregation()
        aufgerufen wird oder der Lauf abgeschlossen ist.
        """
        # ── Aggregation init ──
        self._stop_aggregation.clear()
        self._aggregation_value = 0.0 # Aggregation zurücksetzen
        logger.info("Aggregation gestartet")

        # ── Aggregations-Loop ──
        for i in range(self._config.aggregation.aggregation_max_count):  # 12 × 5s = 60s max
            if self._stop_aggregation.wait(timeout=self._config.aggregation.aggregation_interval_seconds):
                logger.info("Aggregation abgebrochen")
                return

            # Emissionsfaktor threadsicher lesen
            with self._emission_factor_lock:
                factor = self._emission_factor

            # Sensorwert lesen
            sensorread = self._sensor_aas_client.read_sensor_value()
            logger.debug(f"Sensorwert gelesen: {sensorread}")

            # Werte prüfen und Aggregation aktualisieren
            if factor is None:
                logger.warning(f"Schritt {i+1}: kein Emissionsfaktor verfügbar")
            if sensorread is None:
                logger.warning(f"Schritt {i+1}: kein Sensorwert verfügbar")
            else:
                self._aggregation_value += factor * sensorread
                logger.info(f"Schritt {i+1}: aktueller Aggregationswert: {self._aggregation_value}")

        # ── post Aggregation ──
        self._update_aggregation_value()
        logger.info(f"Aggregation abgeschlossen berechneter wert: {self._aggregation_value}")

    def reset_aggregation(self) -> None:
        """Bricht eine laufende Aggregation ab."""
        logger.info("reset_aggregation")
        # self._stop_aggregation.set()
        # logger.info("Aggregation gestoppt")

    def set_scope3_proxy(self) -> None:
        """
        Liest den aktuellen scope3_proxy vom AAS Server
        und speichert ihn lokal für die Aggregation.
        """
        raw = self._aas_client.get_value(
            self._config.scope3_proxy_submodel_id,
            self._config.scope3_proxy_submodelelement_id_short,
        )

        if raw is None:
            logger.error("set_scope3_proxy(): Wert konnte nicht gelesen werden")
            return

        try:
            new_value = float(raw)
        except ValueError:
            logger.error(f"set_scope3_proxy(): Ungültiger Wert '{raw}'")
            return

        # Lock: sicherstellen dass trigger_aggregation() gerade
        # nicht gleichzeitig liest während wir schreiben
        with self._scope3_proxy_lock:
            self._scope3_proxy = new_value

        self._update_total_emission() # Beispiel: Gesamt-Emissionen neu berechnen wenn sich der Proxy ändert

        logger.info(f"Scope3-Proxy aktualisiert: {new_value}")

    # ── Private Operationen ───────────────────────────

    def _update_aggregation_value(self) -> None:
        # TODO: agregierter wert ins AAS zurückschreiben (z.B. in eine Property "aggregatedemission")
        pass
        
    def _update_total_emission(self) -> None:
        # TODO    
        pass

    def _total_scope2_emission(self) -> float:
        # TODO
        pass

    def _update_all(self) -> None:
        # Hilfsmethode um alle Werte zu aktualisieren (z.B. nach einem Reset)
        self.set_emission_factor()
        self.set_scope3_proxy()
        self._aggregation_value = 0.0
        self._total_emission = 0.0