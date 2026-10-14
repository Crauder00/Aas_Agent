"""Normalize events, reconcile watched values and dispatch existing operations."""

from concurrent.futures import ThreadPoolExecutor
import json
import logging
import threading

from ..config.listener_config import SubmodelWatch
from .base_operation_service import BaseOperationService, GuardResult
from .utils.submodel_repository import SubmodelRepository

logger = logging.getLogger(__name__)


class EventHandler:
    """Keep source adapters separate from value comparison and operations."""

    def __init__(self) -> None:
        """Create independent reconciliation and operation workers."""
        self._registry: dict[str, list] = {}
        self._services: list[BaseOperationService] = []
        self._executor = ThreadPoolExecutor(max_workers=10)
        # A separate worker keeps REST and guards out of the MQTT callback.
        self._refresh_executor = ThreadPoolExecutor(max_workers=1)
        self._last_values: dict[object, str] = {}
        self._watches: dict[
            tuple[str, str], tuple[SubmodelRepository, dict, str | None]
        ] = {}
        self._pending: set[tuple[str, str]] = set()
        self._lock = threading.RLock()
        self._draining = False
        self._closed = False

    def register_service(self, service: BaseOperationService) -> None:
        """Register existing service operations without changing their API."""
        self._services.append(service)
        for path, entry in service.get_registry().items():
            self._registry.setdefault(path.lower(), []).append(entry)

    def configure_watches(self, watches: list[SubmodelWatch]) -> None:
        """Use original configured paths for REST, never lowercased paths."""
        for watch in watches:
            key = (watch.base_url.rstrip("/"), watch.submodel_id)
            if key in self._watches:
                raise ValueError("Use one SubmodelWatch per repository/submodel")
            entries: dict[str, list] = {}
            for service in watch.services:
                if not any(service is registered for registered in self._services):
                    raise ValueError("Watched service must be registered with AasAgent")
                for entry in service.get_registry().values():
                    entries.setdefault(entry[0].topic, []).append(entry)
            if not entries:
                raise ValueError("SubmodelWatch requires registered operation paths")
            self._watches[key] = (SubmodelRepository(*key), entries, watch.event_source)

    def initialize_watches(self) -> None:
        """First successful observation establishes a baseline without execution."""
        self._refresh_executor.submit(self._initialize).result()

    def _initialize(self) -> None:
        for key in self._watches:
            self._refresh(key, baseline=True)

    def request_refresh(
        self, submodel_id: str | None = None, source: str | None = None
    ) -> None:
        """Source-independent entry point for MQTT, polling and future adapters."""
        with self._lock:
            if self._closed:
                return
            self._pending.update(
                key
                for key, (_, _, expected_source) in self._watches.items()
                if (submodel_id is None or key[1] == submodel_id)
                and (
                    source is None
                    or expected_source is None
                    or source == expected_source
                )
            )
            if self._pending and not self._draining:
                self._draining = True
                self._refresh_executor.submit(self._drain)

    def _drain(self) -> None:
        while True:
            with self._lock:
                if not self._pending:
                    self._draining = False
                    return
                key = self._pending.pop()
            try:
                self._refresh(key)
            except Exception:
                logger.exception("Could not reconcile submodel %s", key)

    def _refresh(self, key: tuple[str, str], baseline: bool = False) -> None:
        client, paths, _ = self._watches[key]
        for path, entries in paths.items():
            value = client.get_value(path)
            if value is None:
                continue  # Keep last successful observation on REST errors.
            cache_key = (*key, path)
            with self._lock:
                last = self._last_values.get(cache_key)
                self._last_values[cache_key] = value
            if baseline or last is None or value == last:
                continue
            self._dispatch(entries, json.dumps({"value": value}), value, last)

    def handle(self, topic: str, payload: str) -> None:
        """Accept Go CloudEvents or the original Java element topics."""
        try:
            event = json.loads(payload)
        except json.JSONDecodeError, TypeError:
            logger.warning("Invalid JSON on %s", topic)
            return
        if not isinstance(event, dict):
            return
        if "specversion" in event:
            if (
                event.get("specversion") != "1.0"
                or event.get("type") != "io.admin-shell.submodel.updated.v1"
            ):
                return
            data = event.get("data")
            submodel_id = (
                data.get("submodelId") if isinstance(data, dict) else None
            ) or event.get("subject")
            if isinstance(submodel_id, str) and submodel_id:
                source = event.get("source")
                if source is None or isinstance(source, str):
                    self.request_refresh(submodel_id, source)
            return
        path = self._parse_id_short(topic)
        if path is None:
            logger.debug("Unsupported event topic: %s", topic)
            return
        if self._watches:
            # Java also uses reconciliation when watches are configured.
            # The topic identifier can be encoded; checking configured watches
            # avoids coupling this adapter to a particular Java encoding.
            self.request_refresh()
            return
        entries = self._registry.get(path.lower(), [])
        value = self._parse_value(payload)
        with self._lock:
            if self._closed:
                return
            last = self._last_values.get(path.lower())
            if value is not None:
                self._last_values[path.lower()] = value
            self._dispatch(entries, payload, value, last)

    def _dispatch(
        self, entries: list, payload: str, value: str | None, last: str | None
    ) -> None:
        for config, method, guard in entries:
            if not self._should_execute(config.execute_when, value, last):
                continue
            try:
                if guard is not None:
                    result: GuardResult = guard()
                    if not result.proceed:
                        logger.info(
                            "Operation %s blocked: %s",
                            config.method_name,
                            result.reason,
                        )
                        continue
                logger.info(
                    "Operation triggered: %s (via %s)", config.method_name, config.topic
                )
                self._executor.submit(method, payload)
            except Exception:
                logger.exception("Could not dispatch %s", config.method_name)

    def _parse_id_short(self, topic: str) -> str | None:
        parts = topic.split("/")
        if (
            len(parts) == 7
            and parts[2] == "submodels"
            and parts[4] == "submodelElements"
            and parts[6] == "updated"
        ):
            return parts[5]
        return None

    def _parse_value(self, payload: str) -> str | None:
        try:
            value = json.loads(payload).get("value")
            return None if value is None else str(value)
        except json.JSONDecodeError, AttributeError, TypeError:
            return None

    def _should_execute(
        self, execute_when: str, value: str | None, last: str | None
    ) -> bool:
        if execute_when == "everytime":
            return True
        if execute_when == "never":
            return False
        if execute_when in {"onlyontrue", "onlyonfalse"}:
            target = "true" if execute_when == "onlyontrue" else "false"
            return (
                value is not None
                and value.strip().lower() == target
                and (last is None or last.strip().lower() != target)
            )
        logger.warning("Unknown execute_when: %s", execute_when)
        return False

    def close(self) -> None:
        """Finish reconciliation before shutting down operation execution."""
        with self._lock:
            self._closed = True
        self._refresh_executor.shutdown(wait=True)
        self._executor.shutdown(wait=True)
