"""aas_agent.py - Provides the AasAgent class, the central orchestrator of the AAS agent runtime."""

import logging

from .config.aas_agent_config import AgentConfig
from .core.base_operation_service import BaseOperationService
from .core.event_handler import EventHandler
from .core.event_listener import EventListener
from .services.registration_service.registration_service import RegistrationService

logger = logging.getLogger(__name__)


class AasAgent:
    """Orchestriert EmissionService, EventHandler und EventListener."""

    def __init__(
        self,
        agent_config: AgentConfig,
        services: list[BaseOperationService],
    ) -> None:
        """Initialize the AasAgent with configuration and services.

        Args:
            agent_config: Global agent configuration including MQTT and optional registration settings.
            services: List of operation services to register with the EventHandler.
        """
        self._handler = EventHandler()

        # Register all services with the handler
        for service in services:
            self._handler.register_service(service)

        # Subscribe the handler's dispatch method to incoming MQTT events
        self._listener: EventListener = EventListener(
            agent_config.mqtt,
            on_message=self._handler.handle,
        )

        # If no register_config is provided, registration is disabled
        self._registration_service = (
            RegistrationService(agent_config.register_config)
            if agent_config.register_config is not None
            else None
        )

    def start(self) -> None:
        """Start the AAS EventListener and all services."""
        logger.info("AasAgent is starting...")
        self._listener.start()
        logger.info("AasAgent is running.")

    def stop(self) -> None:
        """Stop the AAS EventListener and all services gracefully."""
        logger.info("AasAgent is stopped...")
        self._listener.stop()
        logger.info("AasAgent stopped.")

    def register(self) -> None:
        """Register all Assets and Submodels from the Sub-AAS-Server as Shell Descriptors in the Registry of the Main-AAS-Server."""
        if self._registration_service is None:
            logger.warning("No RegistrationService configured.")
            return
        self._registration_service.register_all()
