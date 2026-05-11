"""submodel_repository.py - simple client to read and write submodel repositorys."""

import json
import logging
from typing import Any

from aas_python_http_client import ApiClient, Configuration, SubmodelRepositoryAPIApi
from aas_python_http_client.util import string_to_base64url
from basyx.aas import model

logger = logging.getLogger(__name__)


class SubmodelRepository:
    """Adapter: Encapsulates the aas-python-http-client library behind a simple get_value/set_value interface."""

    def __init__(self, base_url: str, submodel_repo_id: str | None = None) -> None:
        """Initialize the Client to Enter the Submodle Repository of a defined AAS-Server."""
        configuration = Configuration()
        configuration.host = base_url.rstrip("/")

        api_client = ApiClient(configuration=configuration)
        self._submodel_client = SubmodelRepositoryAPIApi(api_client=api_client)
        self._submodel_repo_id = submodel_repo_id

    def get_value(self, id_short: str) -> str | None:
        """
        Reads a single property value from the AAS Server.

        Args:
            submodel_id: Identifier of the submodel (plain, not Base64)
            id_short: e.g. "ExampleProperty"

        Returns:
            Value as a string, or None on error
        """
        try:
            prop = self._submodel_client.get_submodel_element_by_path_submodel_repo(
                string_to_base64url(self._submodel_repo_id),
                id_short
            )
            value = prop.value
            logger.debug(f"Gelesener Wert '{id_short}': {value}")
            return str(value)

        except Exception as e:
            logger.error(f"Fehler beim Lesen von '{id_short}': {e}")
            return None

    def get_value_list(self, id_short: str) -> list[str] | None:
        """
        Reads all values of a SubmodelElementList from the AAS Server.

        Args:
            id_short: e.g. "ExampleList"

        Returns:
            List of values as strings, or None on error
        """
        try:
            result = self._submodel_client.get_submodel_element_by_path_value_only_submodel_repo(
                submodel_identifier=string_to_base64url(self._submodel_repo_id),
                id_short_path=id_short
            )

            logger.debug(f"Gelesene Liste '{id_short}': {result}")
            return result

        except Exception as e:
            logger.error(f"Fehler beim Lesen von Liste '{id_short}': {e}")
            return None

    def set_value(self, id_short: str, value: Any) -> bool: # noqa: ANN401
        """
        Updates a single property value on the AAS Server.

        Args:
            submodel_id: Identifier of the submodel (plain, not Base64)
            id_short: e.g. "ExampleProperty"
            value: New value

        Returns:
            True on success, False on error
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

    def post_value(self, id_short: str, body: model.Property) -> bool:
        """
        Adds a Property element to a SubmodelElementList.

        Args:
            id_short: IdShortPath to the list, e.g. "ExamplePropertyList"
            body: model.Property object (id_short must be None)

        Returns:
            True on success, False on error
        """
        try:
            self._submodel_client.post_submodel_element_by_path_submodel_repo(
                body,
                submodel_identifier=string_to_base64url(self._submodel_repo_id),
                id_short_path=id_short,
            )
            logger.debug(f"Property (value='{body.value}') erfolgreich zu '{id_short}' hinzugefügt")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen zu '{id_short}': {e}")
            return False
