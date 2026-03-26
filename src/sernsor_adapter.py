import logging
from basyx.aas import model
import basyx.aas.adapter.http as aas_http
from .config import AasConfig

logger = logging.getLogger(__name__)


class SensorAdapter:
    """
    Liest Werte direkt vom AAS Server via BaSyx Python SDK.
    Wir lesen immer vom Server — nie aus der MQTT-Payload.
    """

    def __init__(self, config: AasConfig):
        self._config = config
        # HTTP-Client zum BaSyx REST-Server
        self._client = aas_http.AASServerConnection(config.base_url)

    def get_property_value(
        self,
        submodel_id: str,
        id_short_path: str,
    ) -> str | None:
        """
        Liest einen Property-Wert aus dem AAS Server.

        Args:
            submodel_id:   Identifier des Submodels (nicht Base64, plain)
            id_short_path: idShort des Elements, z.B. "emissionfactor"

        Returns:
            Wert als String, oder None bei Fehler
        """
        try:
            submodel = self._client.get_submodel(submodel_id)
            element = submodel.submodel_element[id_short_path]

            if not isinstance(element, model.Property):
                logger.error(
                    f"Element '{id_short_path}' ist keine Property"
                )
                return None

            logger.debug(
                f"Gelesener Wert '{id_short_path}': {element.value}"
            )
            return element.value

        except Exception as e:
            logger.error(
                f"Fehler beim Lesen von '{id_short_path}': {e}"
            )
            return None