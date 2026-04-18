# emission_service.py

import logging
import threading
from src.core.base_operation_service import BaseOperationService, GuardResult
from .emission_service_config import EmissionServiceConfig
from src.core.utils.submodel_repository import SubmodelRepository
from basyx.aas import model

logger = logging.getLogger(__name__)


class EmissionService(BaseOperationService):
    """
    UseCase: Aggregation von Scope-2 Emissionswerten.
    Operationen werden explizit in __init__ via self.register() angemeldet.
    """

    def __init__(self, config: EmissionServiceConfig):
        self._config = config

        # ── Lokale Zustände ───────────────────────────────────────────────
        self._emission_factor:    float | None = None
        self._aggregation_value:  float | None = None
        self._scope3_proxy:       float | None = None
        self._total_emission:     float | None = None

        self._aggregation_running: bool = False
        self._stop_aggregation = threading.Event()
        self._log_every_n_steps = max(1, round(10 / self._config.aggregation.aggregation_interval_seconds))
        self._log_prefix = f"[Station {self._config.station_index}]"

        # ── Locks ─────────────────────────────────────────────────────────
        self._emission_factor_lock = threading.Lock()
        self._scope3_proxy_lock    = threading.Lock()
        self._aggregation_lock     = threading.Lock()
        self._CFSubmodel_lock      = threading.Lock()

        # ── Clients ───────────────────────────────────────────────────────
        self._aas_client    = SubmodelRepository(self._config.base_url, self._config.submodel_id)
        self._sensor_adapter = SubmodelRepository(self._config.sensor.base_url, self._config.sensor.submodel_id)
        self._product_client = None

        # ── BaseOperationService init (leere Registry) ────────────────────
        super().__init__()

        # ── Operationen anmelden  ─────────────────────────────────────────
        self.register(self.set_emission_factor, topic=self._config.emission_factor_path)
        self.register(self.set_scope3_proxy,    topic=self._config.scope3_proxy_path, execute_when = "never")
        self.register(self._update_current_cf_submodel_path, topic=self._config.currentCFSubmodel_path)
        self.register(
            self.trigger_aggregation,
            topic        = self._config.aggregation_trigger_path,
            execute_when = "onlyontrue",
        )
        self.register(
            self.reset_aggregation,
            topic        = self._config.aggregation_reset_path,
            execute_when = "onlyontrue",
            guard        = self.check_aggregation_running,
        )
        
        self._log_registry_summary()

        # ── Initiale Werte laden ───────────────────────────────────────────
        self._update_all()

    # ── Operationen ───────────────────────────────────────────────────────

    def set_emission_factor(self, payload: str) -> None:
        logger.info(f"{self._log_prefix} Emissionsfaktor vor Aktualisierung: {self._emission_factor}")
        raw = self._aas_client.get_value(self._config.emission_factor_path)

        if raw is None:
            logger.error(f"{self._log_prefix} set_emission_factor(): Wert konnte nicht gelesen werden")
            return
        try:
            new_value = float(raw)
        except ValueError:
            logger.error(f"{self._log_prefix} set_emission_factor(): Ungültiger Wert '{raw}'")
            return

        with self._emission_factor_lock:
            self._emission_factor = new_value
        logger.info(f"{self._log_prefix} Emissionsfaktor aktualisiert: {self._emission_factor}")

    # TODO: mit VdV besprechen von wo der proxy3wert kommen soll??
    def set_scope3_proxy(self, payload: str) -> None:
        # raw = self._aas_client.get_value(self._config.scope3_proxy_path)

        # if raw is None:
        #     logger.error("set_scope3_proxy(): Wert konnte nicht gelesen werden")
        #     return
        # try:
        #     new_value = float(raw)
        # except ValueError:
        #     logger.error(f"set_scope3_proxy(): Ungültiger Wert '{raw}'")
        #     return

        # with self._scope3_proxy_lock:
        #     self._scope3_proxy = new_value
        # logger.info(f"Scope3-Proxy aktualisiert: {new_value}")
        # self._update_total_emission()
        pass

    def trigger_aggregation(self, payload: str) -> None:
        with self._aggregation_lock:
            if self._aggregation_running:
                logger.info(f"{self._log_prefix} Aggregation läuft bereits — ignoriert")
                return
            self._aggregation_running = True

        self._stop_aggregation.clear()
        with self._aggregation_lock:
            self._aggregation_value = 0.0
        logger.info(f"{self._log_prefix} Aggregation gestartet")

        try:
            for i in range(self._config.aggregation.aggregation_max_count):
                if self._stop_aggregation.wait(timeout=self._config.aggregation.aggregation_interval_seconds):
                    logger.info(f"{self._log_prefix} Aggregation wird beendet (Stop-Flag erkannt)")
                    return

                with self._emission_factor_lock:
                    factor = self._emission_factor

                sensorread = self._sensor_adapter.get_value(self._config.sensor.id_short)

                if factor is None:
                    logger.warning(f"{self._log_prefix} Schritt {i+1}: kein Emissionsfaktor verfügbar")
                if sensorread is None:
                    logger.warning(f"{self._log_prefix} Schritt {i+1}: kein Sensorwert verfügbar")
                else:
                    with self._aggregation_lock:
                        try:
                            self._aggregation_value += (
                                float(factor)
                                * float(sensorread)
                                * (float(self._config.aggregation.aggregation_interval_seconds) / 3600.0)
                            )
                        except Exception as e:
                            logger.error(f"{self._log_prefix} Fehler bei Aggregationsberechnung: {e}")
                        logger.debug(f"{self._log_prefix} Schritt {i+1}: Aggregationswert: {self._aggregation_value}")
                        #nur alle ~10sekunden einen wert loggen
                        if (i + 1) % self._log_every_n_steps == 0:
                            logger.info(f"{self._log_prefix} Schritt {i+1}: Aggregationswert: {self._aggregation_value}")
                        
        finally:
            with self._aggregation_lock:
                logger.info(f"{self._log_prefix} Aggregation beendet. Endwert: {self._aggregation_value}")
                self._update_aggregation_value()
                self._aggregation_running = False
                self._aas_client.set_value(self._config.aggregation_trigger_path, "false")

    def reset_aggregation(self, payload: str) -> None:
        self._stop_aggregation.set()
        self._aas_client.set_value(self._config.aggregation_reset_path, "false")
        logger.info(f"{self._log_prefix} Aggregation stopp-Flag gesetzt")

    # ── Guards ────────────────────────────────────────────────────────────

    def check_aggregation_running(self) -> GuardResult:
        with self._aggregation_lock:
            running = self._aggregation_running

        if not running:
            logger.info(f"{self._log_prefix} Reset ignoriert — keine Aggregation aktiv")
            self._aas_client.set_value(self._config.aggregation_reset_path, "false")
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
                    value="https://example.org/ghg/scope2/list/value",
                ),)
            ),
        )
        self._aas_client.post_value(self._config.scope2_list_path, new_prop)
        logger.info(f"{self._log_prefix} Aggregationswert {self._aggregation_value} als neues Element in Scope-2 Liste gepostet")
        self._update_total_emission()

    # TODO: Change _update_total_emission to correctly read out current value and add aggregated value
    def _update_total_emission(self) -> None:
        try:
            scope2_list = self._aas_client.get_value_list(self._config.scope2_list_path)
            scope2sum   = sum(float(v) for v in scope2_list)
        except Exception as e:
            logger.error(f"{self._log_prefix} Fehler beim Berechnen der Scope-2 Summe: {e}")
            scope2sum = 0.0

        with self._scope3_proxy_lock:
            scope3 = self._scope3_proxy or 0.0

        self._total_emission = scope3 + scope2sum

        if self._product_client is None:
            logger.warning("{self._log_prefix} Total Emission nicht aktualisiert: kein Produkt-Submodel verfügbar")
            return

        self._product_client.set_value(self._config.total_emission_path, str(self._total_emission))
        logger.info(f"{self._log_prefix} Total Emission aktualisiert: {self._total_emission}")

    def _update_all(self) -> None:
        self.set_emission_factor(payload="")
        self.set_scope3_proxy(payload="")
        self._update_current_cf_submodel_path()
        self._aggregation_value = 0.0
        self._total_emission    = 0.0

    def _update_current_cf_submodel_path(self) -> bool:
        """Liest den aktuellen CF-Submodel-Pfad aus dem calculation-Submodel und gibt einen Client zurück."""
        raw = self._aas_client.get_value(self._config.currentCFSubmodel_path)

        if not raw or not raw.strip():         # None, leer, nur Whitespace
            logger.warning("{self._log_prefix} currentCFSubmodel_path ist nicht gesetzt oder leer")
            self._product_client = None
            return False
        else:
            with self._CFSubmodel_lock:
                logger.debug(f"{self._log_prefix} currentCFSubmodel_path: '{raw.strip()}'")
                self._product_client = SubmodelRepository(self._config.product_url, raw.strip())
            return True