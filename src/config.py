from dataclasses import dataclass, field


# --- Basis-Klassen ---

@dataclass
class SubmodelElementConfig:
    """Referenz auf ein SubmodelElement innerhalb eines Submodels."""
    submodel_id: str
    id_short: str


@dataclass
class SensorConfig:
    """Verbindungsdaten zu einem Sensor-Repository."""
    base_url: str
    submodel_id: str
    id_short: str


# --- MQTT ---

@dataclass
class MqttConfig:
    host: str                                                                       # Pflichtfeld
    port: int = 1883                                                                # Standard MQTT-Port
    topic_filter: str = "sm-repository/+/submodels/+/submodelElements/+/updated"  # Standard-Filter
    client_id: str = "aas-agent"


# --- AAS ---

@dataclass
class AggregationConfig:
    aggregation_interval_seconds: int = 1    # Intervall zwischen Aggregationsschritten
    aggregation_max_count: int = 300         # Max Anzahl Schritte pro Lauf


@dataclass
class AasConfig:
    """
    Verbindungsdaten zum AAS Repository und Referenzen auf alle
    SubmodelElemente die der Service lesen/schreiben muss.
    """
    base_url: str                               # Pflichtfeld
    emission_factor: SubmodelElementConfig      # Pflichtfeld
    scope3_proxy: SubmodelElementConfig         # Pflichtfeld
    aggregation_value: SubmodelElementConfig    # Pflichtfeld
    aggregation_trigger: SubmodelElementConfig  # Pflichtfeld
    aggregation_reset: SubmodelElementConfig    # Pflichtfeld
    sensor: SensorConfig                        # Pflichtfeld
    aggregation: AggregationConfig = field(default_factory=AggregationConfig)


# --- Top-Level ---

@dataclass
class AgentConfig:
    mqtt: MqttConfig    # Pflichtfeld
    aas: AasConfig      # Pflichtfeld