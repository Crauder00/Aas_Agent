import logging
from .config import AasSensorConfig
from .aas_client import AASClient

logger = logging.getLogger(__name__)


class SensorAdapter:
    """
    Liest Sensorwerte vom externen AAS Server.
    Verwendet call_aas_value — keine direkte SDK-Logik hier.
    """

    def __init__(self, config: AasSensorConfig):
        self._config = config

        self._sensor_client = AASClient(self._config.sensor_url_sm_repository) # Client für Sensor-AAS werte

    def get_sensor_reading(self, id_short: str) -> str | None:
        """
        Liest einen Sensorwert vom externen AAS Server.

        Args:
            id_short: idShort des Elements, z.B. "temperature"

        Returns:
            Wert als String, oder None bei Fehler
        """
        return self._sensor_client.get_value(
            self._config.sensor_submodel_id,
            self._config.sensor_submodelelement_id_short
        )