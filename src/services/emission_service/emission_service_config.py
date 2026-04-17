from dataclasses import dataclass, field

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
    """Alles was EmissionService braucht."""
    base_url: str                   # Pflichtfeld
    submodel_id: str                # Pflichtfeld
    sensor: SubmodelElementConfig   # Pflichtfeld — base_url zeigt auf Sensor-Repository
    emission_factor_path: str       = "emissionfactor"
    scope2_list_path: str           = "scope2emissionslist"
    scope3_proxy_path: str          = "scope3proxy"
    total_emission_path: str        = "totalemissions"
    aggregation_trigger_path: str   = "triggeraggregation"
    aggregation_reset_path: str     = "resetaggregation"
    aggregation: AggregationConfig  = field(default_factory=AggregationConfig)
