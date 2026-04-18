from typing import Final
from src.services.emission_service.emission_service_config import EmissionServiceConfig, SubmodelElementConfig


SENSOR_AAS: Final[str] = "http://localhost:8081"
SENSOR_SUBMODEL_ID: Final[str] = "http://example.com/submodel/carbonfootprint"


config: EmissionServiceConfig = EmissionServiceConfig(
    base_url      = "LOCAL_AAS",
    submodel_id   = "CF_SUBMODEL_ID",
    sensor        = SubmodelElementConfig(SENSOR_AAS, SENSOR_SUBMODEL_ID, "totalemissions"),
    station_index = 1
)

print(config.emission_factor_path)
print(config.currentCFSubmodel_path)
print(config.aggregation_trigger_path)
print(config.aggregation_reset_path)
print(config.scope2_list_path)