"""
This Module should scann the Repository of a sub BaSyx AAS Server and register it as a Shell Discrioptor at the main server.

Status: UNTESTED / UNDEBUGGED
"""

import logging
import time

from aas_python_http_client import (
    ApiClient,
    AssetAdministrationShellRegistryAPIApi,
    AssetAdministrationShellRepositoryAPIApi,
    Configuration,
)
from aas_python_http_client.util import string_to_base64url

logger = logging.getLogger(__name__)


class RegistrationService:
    """Registriert AAS-Descriptoren vom Raspi-Repository beim zentralen Hauptserver."""

    def __init__(self, raspi_base_url: str, raspi_repo_url: str, main_registry_url: str) -> None:
        """Initialisiert die RegistrationService mit den URLs für Raspi-Repository und Hauptserver."""
        self._raspi_base_url = raspi_base_url

        raspi_cfg = Configuration()
        raspi_cfg.host = raspi_repo_url
        raspi_client = ApiClient(configuration=raspi_cfg)
        self._aas_repo = AssetAdministrationShellRepositoryAPIApi(api_client=raspi_client)

        main_cfg = Configuration()
        main_cfg.host = main_registry_url
        main_client = ApiClient(configuration=main_cfg)
        self._main_registry = AssetAdministrationShellRegistryAPIApi(api_client=main_client)

    def register_all(self, retry_interval: int = 5) -> None:
        """Registriert oder aktualisiert alle AAS des Raspi beim Hauptserver."""
        self._wait_for_raspi(retry_interval)

        all_aas = self._aas_repo.get_all_asset_administration_shells().result
        logger.info(f"{len(all_aas)} AAS gefunden auf dem Raspi.")

        for aas in all_aas:
            descriptor = self._build_descriptor(aas)
            self._upsert_descriptor(aas.id, descriptor)

    def _wait_for_raspi(self, retry_interval: int) -> None:
        while True:
            try:
                self._aas_repo.get_all_asset_administration_shells()
                logger.info("Raspi-Server erreichbar.")
                return
            except Exception:
                logger.warning("Warte auf Raspi-Server...")
                time.sleep(retry_interval)

    def _build_descriptor(self, aas: dict) -> dict:
        submodel_refs = self._aas_repo.get_all_submodel_references_aas_repository(
            string_to_base64url(aas.id)
        ).result

        submodel_descriptors = [
            {
                "id": ref.key[0].value,
                "endpoints": [{
                    "interface": "SUBMODEL-3.0",
                    "protocolInformation": {
                        "href": f"{self._raspi_base_url}/api/v3.0/submodels/{string_to_base64url(ref.key[0].value)}"
                    },
                }],
            }
            for ref in submodel_refs
        ]

        return {
            "id": aas.id,
            "assetInformation": {
                "assetKind": aas.asset_information.asset_kind.value,
                "globalAssetId": aas.asset_information.global_asset_id,
            },
            "endpoints": [{
                "interface": "AAS-3.0",
                "protocolInformation": {
                    "href": f"{self._raspi_base_url}/api/v3.0/shells/{string_to_base64url(aas.id)}"
                },
            }],
            "submodelDescriptors": submodel_descriptors,
        }

    def _upsert_descriptor(self, aas_id: str, descriptor: dict) -> None:
        encoded_id = string_to_base64url(aas_id)
        try:
            self._main_registry.get_asset_administration_shell_descriptor_by_id(
                aas_identifier=encoded_id
            )
            self._main_registry.put_asset_administration_shell_descriptor_by_id(
                body=descriptor,
                aas_identifier=encoded_id,
            )
            logger.info(f"Aktualisiert: {aas_id}")
        except Exception:
            self._main_registry.post_asset_administration_shell_descriptor(body=descriptor)
            logger.info(f"Neu registriert: {aas_id}")
