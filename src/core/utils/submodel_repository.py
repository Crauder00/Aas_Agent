# src/core/utils/submodel_repository.py

import logging
from typing import Any

from aas_python_http_client import ApiClient, Configuration, SubmodelRepositoryAPIApi
from aas_python_http_client.util import string_to_base64url
import json

logger = logging.getLogger(__name__)


class SubmodelRepository:
    """
    Adapter: Kapselt die aas-python-http-client Library hinter einer
    einfachen get_value / set_value Schnittstelle.
    """

    def __init__(self, base_url: str, submodel_repo_id: str | None = None):
        configuration = Configuration()
        configuration.host = base_url.rstrip("/")

        api_client = ApiClient(configuration=configuration)
        self._submodel_client = SubmodelRepositoryAPIApi(api_client=api_client)
        self._submodel_repo_id = submodel_repo_id

    def get_value(self, id_short: str) -> str | None:
        """
        Liest einen einzelnen Property-Wert vom AAS Server.

        Args:
            submodel_id: Identifier des Submodels (plain, nicht Base64)
            id_short:    z.B. "ExampleProperty"

        Returns:
            Wert als String, oder None bei Fehler
        """
        try:
            submodel = self._submodel_client.get_submodel_by_id(
                string_to_base64url(self._submodel_repo_id)
            )
            prop = submodel.submodel_element.get("id_short", id_short)
            value = prop.value
            logger.debug(f"Gelesener Wert '{id_short}': {value}")
            return str(value)

        except Exception as e:
            logger.error(f"Fehler beim Lesen von '{id_short}': {e}")
            return None

    def set_value(self, id_short: str, value: Any) -> bool:
        """
        Aktualisiert einen einzelnen Property-Wert auf dem AAS Server.

        Args:
            submodel_id: Identifier des Submodels (plain, nicht Base64)
            id_short:    z.B. "ExampleProperty"
            value:       Neuer Wert

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            self._submodel_client.patch_submodel_element_by_path_value_only_submodel_repo(
                json.dumps(str(value)),
                string_to_base64url(self._submodel_repo_id),
                id_short,
            )
            logger.debug(f"Wert '{id_short}' erfolgreich auf '{value}' gesetzt")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Schreiben von '{id_short}': {e}")
            return False