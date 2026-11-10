"""Fixed-rate service scheduling, independent of MQTT and event workers."""

from collections.abc import Callable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
import logging
import math
import threading
import time

from .base_operation_service import BaseOperationService
from .periodic_operation import PeriodicOperation

logger = logging.getLogger(__name__)


@dataclass
class _Job:
    operation: PeriodicOperation
    name: str
    next_due: float = 0.0
    executor: ThreadPoolExecutor | None = None
    future: Future | None = None


class OperationScheduler:
    """Own one timer and one dedicated worker per registered operation.

    Dedicated workers isolate jobs from event traffic and from each other.
    At most one invocation per registration is pending or running. Hard timing
    detects start deadline misses, but cannot guarantee execution deadlines.
    """

    def __init__(
        self,
        services: Sequence[BaseOperationService],
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Snapshot registrations; defer creating threads until start()."""
        self._clock = clock
        self._jobs = [
            _Job(
                operation,
                f"{type(service).__name__}[{index}]."
                f"{getattr(operation.method, '__name__', type(operation.method).__name__)}",
            )
            for index, service in enumerate(services)
            for operation in service.get_periodic_operations()
        ]
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._closed = False
        self._callback_context = threading.local()
        self._shutdown_lock = threading.Lock()
        self._shutdown_thread: threading.Thread | None = None

    def start(self) -> None:
        """Anchor intervals at startup; repeated starts are harmless."""
        if self._closed:
            raise RuntimeError("A stopped scheduler cannot be restarted")
        if self._thread is not None or not self._jobs:
            return
        origin = self._clock()
        for index, job in enumerate(self._jobs):
            job.next_due = origin + job.operation.interval_seconds
            job.executor = ThreadPoolExecutor(
                max_workers=1, thread_name_prefix=f"aas-periodic-{index}"
            )
        self._thread = threading.Thread(
            target=self._run, name="aas-scheduler", daemon=True
        )
        self._thread.start()

    def request_stop(self) -> None:
        """Prevent further invocations without waiting for running methods."""
        self._closed = True
        self._stop.set()

    def stop(self) -> None:
        """Stop dispatch, cancel queued calls and wait for running calls.

        A periodic method or guard initiates shutdown asynchronously so its own
        worker can return. External callers, including repeated stop() calls,
        wait for the shared shutdown thread to finish joining every executor.
        Running Python methods cannot be forcibly interrupted. Service I/O must
        use timeouts so graceful shutdown can finish.
        """
        self.request_stop()
        with self._shutdown_lock:
            if self._shutdown_thread is None:
                self._shutdown_thread = threading.Thread(
                    target=self._shutdown, name="aas-scheduler-shutdown", daemon=False
                )
                self._shutdown_thread.start()
            shutdown_thread = self._shutdown_thread
        if not getattr(self._callback_context, "active", False):
            shutdown_thread.join()

    def _shutdown(self) -> None:
        """Join the timer and every executor from outside callback workers."""
        if self._thread is not None:
            self._thread.join()
        for job in self._jobs:
            if job.executor is not None:
                job.executor.shutdown(wait=True, cancel_futures=True)

    def _run(self) -> None:
        while not self._stop.is_set():
            now = self._clock()
            self._dispatch_due(now)
            delay = max(0.0, min(job.next_due for job in self._jobs) - self._clock())
            self._stop.wait(delay)

    def _dispatch_due(self, now: float) -> None:
        for job in self._jobs:
            if self._stop.is_set():
                return
            if now < job.next_due:
                continue
            operation = job.operation
            missed = math.floor((now - job.next_due) / operation.interval_seconds)
            scheduled = job.next_due + missed * operation.interval_seconds
            job.next_due = scheduled + operation.interval_seconds
            if missed:
                self._report_miss(job, "coalesced %d missed interval(s)", missed)
            if job.future is not None and not job.future.done():
                self._report_miss(
                    job, "skipped: previous invocation still pending/running"
                )
                continue
            job.future = job.executor.submit(self._invoke, job, scheduled)

    def _report_miss(self, job: _Job, message: str, *args: object) -> None:
        level = logging.ERROR if job.operation.timing == "hard" else logging.WARNING
        logger.log(level, "Periodic operation %s: " + message, job.name, *args)

    def _invoke(self, job: _Job, scheduled: float) -> None:
        operation = job.operation
        self._callback_context.active = True
        try:
            if self._stop.is_set():
                return
            if operation.guard is not None:
                result = operation.guard()
                if not result.proceed:
                    logger.info(
                        "Periodic operation %s blocked: %s", job.name, result.reason
                    )
                    return
            started = self._clock()
            lateness = max(0.0, started - scheduled)
            if (
                operation.max_lateness_seconds is not None
                and lateness > operation.max_lateness_seconds
            ):
                self._report_miss(job, "start deadline exceeded by %.6fs", lateness)
                if operation.timing == "hard" and operation.late_policy == "skip":
                    return
            if self._stop.is_set():
                return
            logger.debug(
                "Periodic operation %s starting; lateness=%.6fs", job.name, lateness
            )
            try:
                operation.method()
            finally:
                logger.debug(
                    "Periodic operation %s finished; runtime=%.6fs",
                    job.name,
                    self._clock() - started,
                )
        except Exception:
            logger.exception("Periodic operation %s failed", job.name)
        finally:
            self._callback_context.active = False
