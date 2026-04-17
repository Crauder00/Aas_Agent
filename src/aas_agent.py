import logging

from src.aas_agent_config import AgentConfig
from src.core.event_handler import EventHandler
from src.core.event_listener import EventListener
from src.services.emission_service.emission_service import EmissionService
from src.services.emission_service.emission_service_config import EmissionServiceConfig
from src.services.registration_service.registration_service import RegistrationService

logger = logging.getLogger(__name__)


class AasAgent:
    """Orchestriert EmissionService, EventHandler und EventListener."""

    def __init__(
        self,
        agent_config: AgentConfig,
        emission_config: EmissionServiceConfig,
    ) -> None:
        self._service: EmissionService = EmissionService(emission_config)
        self._handler: EventHandler = EventHandler(self._service)
        self._listener: EventListener = EventListener(
            agent_config.mqtt,
            on_message=self._handler.handle,
        )

        #falls kein register_config vorhanden, wird None Konfiguriert
        self._registration_service = (
        RegistrationService(agent_config.register_config)
        if agent_config.register_config is not None
        else None
    )   

    def start(self) -> None:
        logger.info("AasAgent wird gestartet...")
        self._listener.start()
        logger.info("AasAgent läuft.")

    def stop(self) -> None:
        logger.info("AasAgent wird gestoppt...")
        self._listener.stop()
        logger.info("AasAgent gestoppt.")

    def register(self) -> None:
        if self._registration_service is None:
            logger.warning("Kein RegistrationService konfiguriert.")
            return
        self._registration_service.register_all()