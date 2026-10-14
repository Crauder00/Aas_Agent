"""Configuration for event sources and explicit submodel/service bindings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from .mqtt_config import MqttConfig

if TYPE_CHECKING:
    from ..core.base_operation_service import BaseOperationService


@dataclass
class SubmodelWatch:
    """Explicit binding to services already registered with AasAgent.

    base_url is the REST repository URL as used by SubmodelRepository.
    event_source optionally matches CloudEvent.source exactly, useful when
    different repositories publish the same submodel ID to one broker.
    """

    base_url: str
    submodel_id: str
    services: list[BaseOperationService]
    event_source: str | None = None


@dataclass
class ListenerConfig(MqttConfig):
    """Optional reconciliation settings; existing MqttConfig remains supported.

    watches explicitly bind repositories/submodels to registered service instances.
    topic_filter may be a string or a list of MQTT filters (Java and Go together).
    Future event sources can call EventHandler.request_refresh directly.
    """

    mode: Literal["mqtt", "polling"] = "mqtt"
    poll_interval_seconds: float = 1.0
    watches: list[SubmodelWatch] = field(default_factory=list)
    topic_filter: str | list[str] = "basyx/submodelrepository/submodel/updated"
