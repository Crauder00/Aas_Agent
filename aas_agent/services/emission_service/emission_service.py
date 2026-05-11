"""emission_service-py - Service for aggregating Scope-2 emission values based on sensor readings and an emission factor."""

import logging
import threading

from basyx.aas import model

from ...config.emission_service_config import EmissionServiceConfig
from ...core.base_operation_service import BaseOperationService, GuardResult
from ...core.utils.submodel_repository import SubmodelRepository

logger = logging.getLogger(__name__)


class EmissionService(BaseOperationService):
    """Service for aggregating Scope-2 emission values.

    Operations are explicitly registered in __init__ via self.register().
    Each operation is bound to a topic (idShort) and triggered by the EventHandler
    when a matching MQTT message is received.
    """

    def __init__(self, config: EmissionServiceConfig) -> None:
        """Initialize the EmissionService with the given configuration.

        Args:
            config: Configuration for this emission service instance,
                    including AAS URLs, submodel IDs, sensor path, and aggregation settings.
        """
        self._config = config

        # ── Local state ───────────────────────────────────────────────────
        self._emission_factor:   float | None = None
        self._aggregation_value: float | None = None
        self._pcfco2eq:          float | None = None

        self._aggregation_running: bool = False
        self._stop_aggregation = threading.Event()
        self._log_every_n_steps = max(1, round(10 / self._config.aggregation.aggregation_interval_seconds))
        self._log_prefix = f"[Station {self._config.station_index}]"

        # ── Locks ─────────────────────────────────────────────────────────
        self._emission_factor_lock = threading.Lock()
        self._aggregation_lock     = threading.Lock()
        self._CFSubmodel_lock      = threading.Lock()

        # ── Clients ───────────────────────────────────────────────────────
        self._aas_client     = SubmodelRepository(self._config.base_url, self._config.submodel_id)
        self._sensor_adapter = SubmodelRepository(self._config.sensor.base_url, self._config.sensor.submodel_id)
        self._product_client = None

        # ── BaseOperationService init (empty registry) ────────────────────
        super().__init__()

        # ── Register operations ───────────────────────────────────────────
        self.register(self.set_emission_factor, topic=self._config.emission_factor_path)
        self.register(self.update_current_cf_submodel_path, topic=self._config.current_cf_submodel_path)
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

        # ── Load initial values ────────────────────────────────────────────
        self._update_all()

    # ── Operations ────────────────────────────────────────────────────────

    def set_emission_factor(self, payload: str) -> None:
        """Read and update the emission factor from the AAS submodel.

        Args:
            payload: Raw MQTT payload (unused; value is read directly from AAS).
        """
        logger.info(f"{self._log_prefix} Emission factor before update: {self._emission_factor}")
        raw = self._aas_client.get_value(self._config.emission_factor_path)

        if raw is None:
            logger.error(f"{self._log_prefix} set_emission_factor(): could not read value")
            return
        try:
            new_value = float(raw)
        except ValueError:
            logger.error(f"{self._log_prefix} set_emission_factor(): invalid value '{raw}'")
            return

        with self._emission_factor_lock:
            self._emission_factor = new_value
        logger.info(f"{self._log_prefix} Emission factor updated: {self._emission_factor}")

    def update_current_cf_submodel_path(self, payload: str = "") -> None:
        """Read the current CF submodel path from the AAS and initialize the product client.

        Args:
            payload: Raw MQTT payload (unused).
        """
        raw = self._aas_client.get_value(self._config.current_cf_submodel_path)

        if not raw or not raw.strip():
            logger.warning(f"{self._log_prefix} current_cf_submodel_path is not set or empty")
            self._product_client = None
            return

        with self._CFSubmodel_lock:
            logger.info(f"{self._log_prefix} current_cf_submodel_path: '{raw.strip()}'")
            self._product_client = SubmodelRepository(self._config.product_url, raw.strip())
        return

    def trigger_aggregation(self, payload: str) -> None:
        """Start the aggregation loop, accumulating emission values over time.

        Reads the sensor value and emission factor at each interval and accumulates
        the product into the aggregation value. Writes the final result to the AAS
        once the loop completes or is stopped.

        Args:
            payload: Raw MQTT payload (unused; aggregation is triggered by topic).
        """
        with self._aggregation_lock:
            if self._aggregation_running:
                logger.info(f"{self._log_prefix} Aggregation already running — ignored")
                return
            self._aggregation_running = True

        self._stop_aggregation.clear()
        with self._aggregation_lock:
            self._aggregation_value = 0.0
        logger.info(f"{self._log_prefix} Aggregation started")

        try:
            for i in range(self._config.aggregation.aggregation_max_count):
                if self._stop_aggregation.wait(timeout=self._config.aggregation.aggregation_interval_seconds):
                    logger.debug(f"{self._log_prefix} Aggregation stopping (stop flag detected)")
                    return

                with self._emission_factor_lock:
                    factor = self._emission_factor

                sensorread = self._sensor_adapter.get_value(self._config.sensor.id_short)

                if factor is None:
                    logger.warning(f"{self._log_prefix} Step {i+1}: no emission factor available")
                if sensorread is None:
                    logger.warning(f"{self._log_prefix} Step {i+1}: no sensor value available")
                else:
                    with self._aggregation_lock:
                        try:
                            self._aggregation_value += (
                                float(factor)
                                * float(sensorread)
                                * (float(self._config.aggregation.aggregation_interval_seconds) / 3600.0)
                            )
                        except Exception as e:
                            logger.error(f"{self._log_prefix} Error during aggregation calculation: {e}")
                        logger.debug(f"{self._log_prefix} Step {i+1}: aggregation value: {self._aggregation_value}")
                        # Log only every ~10 seconds to reduce noise
                        if (i + 1) % self._log_every_n_steps == 0:
                            logger.info(f"{self._log_prefix} Step {i+1}: aggregation value: {self._aggregation_value}")

        finally:
            with self._aggregation_lock:
                logger.info(f"{self._log_prefix} Aggregation finished. Final value: {self._aggregation_value}")
                self._update_aggregation_value()
                self._update_pcfco2eq()
                self._aggregation_running = False
                self._aas_client.set_value(self._config.aggregation_trigger_path, "false")
                logger.debug("end of trigger_aggregation()")

    def reset_aggregation(self, payload: str) -> None:
        """Stop the running aggregation by setting the stop flag.

        Args:
            payload: Raw MQTT payload (unused).
        """
        self._stop_aggregation.set()
        self._aas_client.set_value(self._config.aggregation_reset_path, "false")
        logger.debug(f"{self._log_prefix} Aggregation stop flag set")

    # ── Guards ────────────────────────────────────────────────────────────

    def check_aggregation_running(self) -> GuardResult:
        """Guard for reset_aggregation - only proceed if aggregation is currently active.

        Returns:
            GuardResult with proceed=True if aggregation is running, False otherwise.
        """
        with self._aggregation_lock:
            running = self._aggregation_running

        if not running:
            logger.info(f"{self._log_prefix} Reset ignored — no aggregation active")
            self._aas_client.set_value(self._config.aggregation_reset_path, "false")
            return GuardResult(proceed=False, reason="No aggregation active")

        return GuardResult(proceed=True)

    # ── Private helpers ───────────────────────────────────────────────────

    def _update_aggregation_value(self) -> None:
        """Post the accumulated aggregation value as a new entry in the Scope-2 list and update PcfCO2eq."""
        logger.debug("update_aggregation_value() called")
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
        logger.info(f"{self._log_prefix} Aggregation value {self._aggregation_value} posted as new entry in Scope-2 list")

    def _update_pcfco2eq(self) -> None:
        """Add the current aggregation value to the existing PcfCO2eq in the product submodel."""
        # Copy client reference for thread safety
        with self._CFSubmodel_lock:
            client = self._product_client
        if client is None:
            logger.warning(f"{self._log_prefix} PcfCO2eq not updated: no product submodel available")
            return

        logger.debug(f"{self._log_prefix} Current aggregation value for PcfCO2eq update: {self._aggregation_value}")

        try:
            current_cf_value = client.get_value(self._config.pcfco2eq_path)
            current_cf_value = float(current_cf_value) if current_cf_value is not None else 0.0
            logger.debug(f"{self._log_prefix} Current PcfCO2eq value: {current_cf_value}")
        except Exception as e:
            logger.error(f"{self._log_prefix} Error reading current carbon footprint value: {e}")
            current_cf_value = 0.0

        self._pcfco2eq = current_cf_value + self._aggregation_value
        logger.debug(f"{self._log_prefix} New PcfCO2eq value calculated: {self._pcfco2eq}")
        client.set_value(self._config.pcfco2eq_path, str(self._pcfco2eq))
        logger.info(f"{self._log_prefix} PcfCO2eq updated: {self._pcfco2eq}")

    def _update_all(self) -> None:
        """Load all initial values from the AAS on service startup."""
        self.set_emission_factor(payload="")
        self.update_current_cf_submodel_path()
        self._aggregation_value = 0.0
        self._pcfco2eq          = 0.0

