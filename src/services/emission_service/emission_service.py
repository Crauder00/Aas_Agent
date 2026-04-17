import logging
import threading
from src.core.base_operation_service import BaseOperationService, operation, GuardResult
from .emission_service_config import EmissionServiceConfig
from src.core.utils.submodel_repository import SubmodelRepository
from basyx.aas import model

logger = logging.getLogger(__name__)


class EmissionService(BaseOperationService):
    """
    UseCase: Aggregation von Scope-2 Emissionswerten.
    Registriert seine Operationen automatisch via @operation Dekorator.
    """

    def __init__(self, config: EmissionServiceConfig):
        self._config: EmissionServiceConfig = config

        # ── Lokale Zustände ───────────────────────────────────────────────
        self._emission_factor: float | None = None
        self._scope3_proxy: float | None = None
        self._aggregation_value: float | None = None
        self._total_emission: float | None = None
        self._aggregation_running: bool = False
        self._stop_aggregation: threading.Event = threading.Event()

        # ── Locks ─────────────────────────────────────────────────────────
        self._emission_factor_lock: threading.Lock = threading.Lock()
        self._scope3_proxy_lock: threading.Lock = threading.Lock()
        self._aggregation_lock: threading.Lock = threading.Lock()

        # ── Clients ───────────────────────────────────────────────────────
        self._aas_client: SubmodelRepository = SubmodelRepository(self._config.base_url, self._config.submodel_id)
        self._sensor_adapter: SubmodelRepository = SubmodelRepository(self._config.sensor.base_url, self._config.sensor.submodel_id)

        # ── Init: BaseOperationService aufrufen (baut Registry auf) ───────
        super().__init__()

        # ── Initiale Werte laden ───────────────────────────────────────────
        self._update_all()

    # ── Operationen (via @operation registriert) ──────────────────────────

    @operation(topic="emissionfactor", execute_when="everytime")
    def set_emission_factor(self, payload: str) -> None:
        """Liest den aktuellen Emissionsfaktor vom AAS und speichert ihn lokal."""
        logger.info(f"Emissionsfaktor vor Aktualisierung: {self._emission_factor}")

        raw = self._aas_client.get_value(
            self._config.emission_factor_path
        )

        if raw is None:
            logger.error("set_emission_factor(): Wert konnte nicht gelesen werden")
            return

        try:
            new_value = float(raw)
        except ValueError:
            logger.error(f"set_emission_factor(): Ungültiger Wert '{raw}'")
            return

        with self._emission_factor_lock:
            self._emission_factor = new_value

        logger.info(f"Emissionsfaktor aktualisiert: {self._emission_factor}")

    @operation(topic="scope3proxy", execute_when="everytime")
    def set_scope3_proxy(self, payload: str) -> None:
        """Liest den aktuellen Scope3-Proxy vom AAS und speichert ihn lokal."""
        raw = self._aas_client.get_value(
            self._config.scope3_proxy_path
        )

        if raw is None:
            logger.error("set_scope3_proxy(): Wert konnte nicht gelesen werden")
            return

        try:
            new_value = float(raw)
        except ValueError:
            logger.error(f"set_scope3_proxy(): Ungültiger Wert '{raw}'")
            return

        with self._scope3_proxy_lock:
            self._scope3_proxy = new_value

        logger.info(f"Scope3-Proxy aktualisiert: {new_value}")
        self._update_total_emission()
        

    @operation(topic="triggeraggregation", execute_when="onlyontrue")
    def trigger_aggregation(self, payload: str) -> None:
        """Startet die Aggregation."""
        with self._aggregation_lock:
            if self._aggregation_running:
                logger.info("Aggregation läuft bereits — ignoriert")
                return
            self._aggregation_running = True

        self._stop_aggregation.clear()
        with self._aggregation_lock:
            self._aggregation_value = 0.0
        logger.info("Aggregation gestartet")

        try:
            for i in range(self._config.aggregation.aggregation_max_count):
                if self._stop_aggregation.wait(timeout=self._config.aggregation.aggregation_interval_seconds):
                    logger.info("Aggregation wird beendet (Stop-Flag erkannt)")
                    return

                with self._emission_factor_lock:
                    factor = self._emission_factor

                # sensorread = self._sensor_adapter.get_sensor_reading()
                sensorread = self._sensor_adapter.get_value(
                    self._config.sensor.id_short
                )


                if factor is None:
                    logger.warning(f"Schritt {i+1}: kein Emissionsfaktor verfügbar")
                if sensorread is None:
                    logger.warning(f"Schritt {i+1}: kein Sensorwert verfügbar")
                else:
                    with self._aggregation_lock:
                        try:
                            self._aggregation_value += (
                                float(factor)
                                * float(sensorread)
                                * (float(self._config.aggregation.aggregation_interval_seconds) / 3600.0)
                            )
                        except Exception as e:
                            logger.error(f"Fehler bei Aggregationsberechnung: {e}")
                        logger.info(f"Schritt {i+1}: Aggregationswert: {self._aggregation_value}")
        finally:
            with self._aggregation_lock:
                logger.info(f"Aggregation beendet. Endwert: {self._aggregation_value}")
                self._update_aggregation_value()
                self._aggregation_running = False
                self._aas_client.set_value(
                    self._config.aggregation_trigger_path,
                    "false",
                )

    @operation(topic="resetaggregation", execute_when="onlyontrue", guard="check_aggregation_running")
    def reset_aggregation(self, payload: str) -> None:
        """Bricht eine laufende Aggregation ab."""
        self._stop_aggregation.set()
        self._aas_client.set_value(
                self._config.aggregation_reset_path,
                "false",
            )
        logger.info("Aggregation stopp-Flag gesetzt")

    # ── Guards ────────────────────────────────────────────────────────────

    def check_aggregation_running(self) -> GuardResult:
        """Guard für reset_aggregation: prüft ob überhaupt eine Aggregation läuft."""
        with self._aggregation_lock:
            running = self._aggregation_running

        if not running:
            logger.info("Reset ignoriert — keine Aggregation aktiv")
            self._aas_client.set_value(
                self._config.aggregation_reset_path,
                "false",
            )
            return GuardResult(proceed=False, reason="Keine Aggregation aktiv")

        return GuardResult(proceed=True)

    # ── Private Hilfsmethoden ─────────────────────────────────────────────

    def _update_aggregation_value(self) -> None:
        new_prop = model.Property(
            id_short=None,
            value_type=model.datatypes.Float,
            value=self._aggregation_value,
            semantic_id=model.ExternalReference(
                (model.Key(
                    type_=model.KeyTypes.GLOBAL_REFERENCE,
                    value='https://example.org/ghg/scope2/list/value'
                ),)
            )
        )
        self._aas_client.post_value(self._config.scope2_list_path, new_prop) # uploaden als neues Element in die Liste
        logger.info(f"Aggregationswert {self._aggregation_value} als neues Element in Scope-2 Liste gepostet")
        self._update_total_emission() # aufrufen, damit TotalEmission immer aktuell ist
    

    def _update_total_emission(self) -> None:
        try:
            scope2_list = self._aas_client.get_value_list(self._config.scope2_list_path) # Liste aller Scope-2 Werte lesen
            scope2sum = sum(float(value) for value in scope2_list) # Summe aller Scope-2 Werte berechnen
        except Exception as e:
            logger.error(f"Fehler beim Berechnen der Scope-2 Summe: {e}")
            scope2sum = 0.0
        
        # Gesamt berechnen
        self._total_emission = self._scope3_proxy + scope2sum

        # zurück ins AAS schreiben
        self._aas_client.set_value(
            self._config.total_emission_path,
            str(self._total_emission)
        )
        logger.info(f"Total Emission aktualisiert: {self._total_emission}")

    def _update_all(self) -> None:
        """Initiale Werte beim Start laden."""
        self.set_emission_factor(payload="")
        self.set_scope3_proxy(payload="")
        self._aggregation_value = 0.0
        self._total_emission = 0.0
