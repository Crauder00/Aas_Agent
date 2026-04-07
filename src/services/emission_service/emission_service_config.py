from dataclasses import dataclass, field
from src.config import SubmodelElementConfig


# --- Scope2-spezifische Konfiguration ---

@dataclass
class AggregationConfig:
    aggregation_interval_seconds: int = 1    # Intervall zwischen Aggregationsschritten
    aggregation_max_count: int = 300         # Max Anzahl Schritte pro Lauf


@dataclass
class EmissionServiceConfig:
    """Alles was EmissionService braucht."""
    emission_factor: SubmodelElementConfig      # Pflichtfeld
    scope2_list: SubmodelElementConfig          # Pflichtfeld
    scope3_proxy: SubmodelElementConfig         # Pflichtfeld
    total_emission: SubmodelElementConfig       # Pflichtfeld
    aggregation_value: SubmodelElementConfig    # Pflichtfeld
    aggregation_trigger: SubmodelElementConfig  # Pflichtfeld
    aggregation_reset: SubmodelElementConfig    # Pflichtfeld
    sensor: SubmodelElementConfig               # Pflichtfeld — base_url zeigt auf Sensor-Repository
    aggregation: AggregationConfig = field(default_factory=AggregationConfig)
