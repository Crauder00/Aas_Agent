import logging
from typing import Final

from src.config import AgentConfig, MqttConfig, SubmodelElementConfig
from src.core.event_handler import EventHandler
from src.core.event_listener import EventListener
from src.services.emission_service.emission_service import EmissionService
from src.services.emission_service.emission_service_config import EmissionServiceConfig

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

    def start(self) -> None:
        logger.info("AasAgent wird gestartet...")
        self._listener.start()
        logger.info("AasAgent läuft.")

    def stop(self) -> None:
        logger.info("AasAgent wird gestoppt...")
        self._listener.stop()
        logger.info("AasAgent gestoppt.")