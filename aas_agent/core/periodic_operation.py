"""Registration metadata for synchronous, periodic service operations."""

from collections.abc import Callable
from dataclasses import dataclass
import inspect
import math
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .base_operation_service import GuardResult


@dataclass(frozen=True)
class PeriodicOperation:
    """Describe an interval and its start deadline, without runtime state.

    Hard timing monitors a deadline; it does not provide real-time guarantees.
    Callbacks and guards must be synchronous and callable without arguments.
    """

    method: Callable[[], None]
    interval_seconds: float
    timing: Literal["soft", "hard"] = "soft"
    max_lateness_seconds: float | None = None
    overlap: Literal["skip"] = "skip"
    late_policy: Literal["skip", "run"] = "skip"
    guard: Callable[[], GuardResult] | None = None

    def __post_init__(self) -> None:
        """Reject invalid schedules before any runtime threads are started."""
        if not math.isfinite(self.interval_seconds) or self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be finite and positive")
        if self.timing not in {"soft", "hard"}:
            raise ValueError("timing must be 'soft' or 'hard'")
        if self.max_lateness_seconds is not None and (
            not math.isfinite(self.max_lateness_seconds)
            or self.max_lateness_seconds < 0
        ):
            raise ValueError("max_lateness_seconds must be finite and nonnegative")
        if self.timing == "hard" and self.max_lateness_seconds is None:
            raise ValueError("hard timing requires max_lateness_seconds")
        if self.overlap != "skip":
            raise ValueError("Only overlap='skip' is supported")
        if self.late_policy not in {"skip", "run"}:
            raise ValueError("late_policy must be 'skip' or 'run'")
        if not callable(self.method):
            raise ValueError("Periodic method must be a synchronous callable")
        for callback in (self.method, self.guard):
            if callback is None:
                continue
            if (
                not callable(callback)
                or inspect.iscoroutinefunction(callback)
                or inspect.iscoroutinefunction(callback.__call__)
                or inspect.isgeneratorfunction(callback)
                or inspect.isasyncgenfunction(callback)
            ):
                raise ValueError("Periodic callbacks must be synchronous callables")
            try:
                inspect.signature(callback).bind()
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "Periodic callbacks must be callable without arguments"
                ) from error
