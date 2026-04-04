import logging
from src.config import SubmodelElementConfig
from src.core.utils.aas_sm_http_client import AasSmHttpClient

logger = logging.getLogger(__name__)


class SensorAdapter:
    """
    Liest Sensorwerte vom externen AAS Server.
    Verwendet AasSmHttpClient — keine direkte SDK-Logik hier.
    """

    def __init__(self, config: SubmodelElementConfig):
        self._config = config
        self._client = AasSmHttpClient(config.base_url)

    def get_sensor_reading(self) -> str | None:
        """
        Liest einen Sensorwert vom externen AAS Server.

        Returns:
            Wert als String, oder None bei Fehler
        """
        try:
            return self._client.get_value(
                self._config.submodel_id,
                self._config.id_short,
            )
        except Exception as e:
            logger.error(f"get_sensor_reading(): Fehler beim Lesen: {e}")
            return None
