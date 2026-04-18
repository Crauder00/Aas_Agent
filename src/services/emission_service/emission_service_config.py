from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SubmodelElementConfig:
    """Referenz auf ein SubmodelElement in irgendeinem AAS-Repository."""
    base_url: str
    submodel_id: str
    id_short: str

# --- Scope2-spezifische Konfiguration ---

@dataclass
class AggregationConfig:
    aggregation_interval_seconds: int = 1    # Intervall zwischen Aggregationsschritten
    aggregation_max_count: int = 300         # Max Anzahl Schritte pro Lauf


@dataclass
class EmissionServiceConfig:
    # Pflichtfelder:
    base_url: str
    product_url: str
    submodel_id: str
    sensor: SubmodelElementConfig
    station_index: int

    # Aggregation Einstellungen
    aggregation: "AggregationConfig" = field(default_factory=lambda: AggregationConfig())

    # optionale Overrides
    scope2_list_path_override: Optional[str] = None
    aggregation_trigger_path_override: Optional[str] = None
    aggregation_reset_path_override: Optional[str] = None
    currentCFSubmodel_override: Optional[str] = None
    emission_factor_path: str = "emissionfactor"
    scope3_proxy_path: str          = "ProductCarbonFootprintProduction.TBD"
    total_emission_path: str        = "ProductCarbonFootprintProduction.PcfCO2eq"

    # Hilfsfunktion zm
    def _station_path(self, suffix: str) -> str:
        return f"Stations[{self.station_index}].{suffix}"

    @property
    def scope2_list_path(self) -> str:
        return self.scope2_list_path_override or self._station_path("scope2emissionslist")

    @property
    def aggregation_trigger_path(self) -> str:
        return self.aggregation_trigger_path_override or self._station_path("triggeraggregation")

    @property
    def aggregation_reset_path(self) -> str:
        return self.aggregation_reset_path_override or self._station_path("resetaggregation")
    
    @property
    def currentCFSubmodel_path(self) -> str:
        return self.currentCFSubmodel_override or self._station_path("currentCFSubmodel")


# @dataclass
# class EmissionServiceConfig:
#     """Alles was EmissionService braucht."""
#     base_url: str                   # Pflichtfeld
#     submodel_id: str                # Pflichtfeld
#     sensor: SubmodelElementConfig   # Pflichtfeld — base_url zeigt auf Sensor-Repository
#     emission_factor_path: str       = "emissionfactor"
#     scope2_list_path: str           = "scope2emissionslist"
#     scope3_proxy_path: str          = "scope3proxy"
#     total_emission_path: str        = "totalemissions"
#     aggregation_trigger_path: str   = "triggeraggregation"
#     aggregation_reset_path: str     = "resetaggregation"
#     aggregation: AggregationConfig  = field(default_factory=AggregationConfig)
