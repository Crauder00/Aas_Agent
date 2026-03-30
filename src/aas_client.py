# src/aas_client.py

import logging
import base64
import requests
from typing import Any

logger = logging.getLogger(__name__)


class AASClient:
    def __init__(self, base_url: str):
        self._base = base_url.rstrip("/")
        self._session = requests.Session()

    def _encode_id(self, submodel_id: str) -> str:
        return base64.urlsafe_b64encode(submodel_id.encode()).decode().rstrip("=")

    def _element_url(self, submodel_id: str, id_short: str) -> str:
        encoded = self._encode_id(submodel_id)
        return f"{self._base}/submodels/{encoded}/submodel-elements/{id_short}/$value"

    def get_value(self, submodel_id: str, id_short: str) -> str | None:
        """
        Liest einen einzelnen Property-Wert vom AAS Server.

        Args:
            submodel_id:  Identifier des Submodels (plain, nicht Base64)
            id_short:     z.B. "emissionfactor" oder "Collection.emissionfactor"

        Returns:
            Wert als String, oder None bei Fehler
        """
        url = self._element_url(submodel_id, id_short)
        try:
            response = self._session.get(url, timeout=10)
            response.raise_for_status()

            value = response.json()
            logger.debug(f"Gelesener Wert '{id_short}': {value}")
            return str(value)

        except requests.HTTPError as e:
            logger.error(f"HTTP-Fehler beim Lesen von '{id_short}': {e.response.status_code} {e.response.reason}")
            return None
        except requests.RequestException as e:
            logger.error(f"Verbindungsfehler beim Lesen von '{id_short}': {e}")
            return None

    def set_value(self, submodel_id: str, id_short: str, value: Any) -> bool:
        """
        Aktualisiert einen einzelnen Property-Wert auf dem AAS Server.

        Args:
            submodel_id:  Identifier des Submodels (plain, nicht Base64)
            id_short:     z.B. "emissionfactor" oder "Collection.emissionfactor"
            value:        Neuer Wert (wird als JSON gesendet)

        Returns:
            True bei Erfolg, False bei Fehler
        """
        url = self._element_url(submodel_id, id_short)
        try:
            response = self._session.patch(url, json=value, timeout=10)
            response.raise_for_status()

            logger.debug(f"Wert '{id_short}' erfolgreich auf '{value}' gesetzt")
            return True

        except requests.HTTPError as e:
            logger.error(f"HTTP-Fehler beim Schreiben von '{id_short}': {e.response.status_code} {e.response.reason}")
            return False
        except requests.RequestException as e:
            logger.error(f"Verbindungsfehler beim Schreiben von '{id_short}': {e}")
            return False