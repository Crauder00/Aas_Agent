"""emission_service_config.py - Configuration classes for the emission service."""

from dataclasses import dataclass, field


@dataclass
class SubmodelElementConfig:
    """Reference to a SubmodelElement in any AAS repository."""
    base_url: str
    submodel_id: str
    id_short: str


@dataclass
class AggregationConfig:
    """Configuration for aggregation settings in the emission service."""
    aggregation_interval_seconds: int = 1    # Intervall zwischen Aggregationsschritten
    aggregation_max_count: int = 300         # Max Anzahl Schritte pro Lauf


@dataclass
class EmissionServiceConfig:
    """Configuration for the emission service."""
    # Mandatory fields:
    base_url: str
    product_url: str
    submodel_id: str
    sensor: SubmodelElementConfig
    station_index: int

    # Aggregation settings
    aggregation: AggregationConfig = field(default_factory=lambda: AggregationConfig())

    # Optional overrides for default paths
    scope2_list_path_override: str | None = None
    aggregation_trigger_path_override: str | None = None
    aggregation_reset_path_override: str | None = None
    current_cf_submodel_override: str | None = None
    emission_factor_path: str = "emissionfactor"
    pcfco2eq_path: str        = "ProductCarbonFootprintProduction.PcfCO2eq"

    # Helper function for generating station paths
    def _station_path(self, suffix: str) -> str:
        """Generate the station path with the given suffix."""
        return f"Stations[{self.station_index}].{suffix}"

    # Setts the default paths based on the station index if no overrides are provided
    @property
    def scope2_list_path(self) -> str:
        """Get the scope2 list path, using override if available."""
        return self.scope2_list_path_override or self._station_path("scope2emissionslist")

    @property
    def aggregation_trigger_path(self) -> str:
        """Get the aggregation trigger path, using override if available."""
        return self.aggregation_trigger_path_override or self._station_path("triggeraggregation")

    @property
    def aggregation_reset_path(self) -> str:
        """Get the aggregation reset path, using override if available."""
        return self.aggregation_reset_path_override or self._station_path("resetaggregation")

    @property
    def current_cf_submodel_path(self) -> str:
        """Get the current Carbon Footprint submodel path, using override if available."""
        return self.current_cf_submodel_override or self._station_path("currentCFSubmodel")

