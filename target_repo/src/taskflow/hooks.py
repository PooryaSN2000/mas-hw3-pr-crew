"""Lifecycle event hook system for observing and extending workflow execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import threading
import time
from typing import Any, Callable, Dict, List

from taskflow.models import HookError


class HookEvent(str, Enum):
    """Lifecycle events emitted during workflow execution."""

    BEFORE_WORKFLOW = "before_workflow"
    AFTER_WORKFLOW = "after_workflow"
    BEFORE_TASK = "before_task"
    AFTER_TASK = "after_task"
    ON_RETRY = "on_retry"
    ON_CACHE_HIT = "on_cache_hit"
    ON_ERROR = "on_error"


HookCallback = Callable[[HookEvent, Dict[str, Any]], None]


class HookManager:
    """Thread-safe publisher of lifecycle events to registered subscribers."""

    def __init__(self, strict: bool = False) -> None:
        self.strict = strict
        self._lock = threading.RLock()
        self._listeners: Dict[HookEvent, List[HookCallback]] = {
            event: [] for event in HookEvent
        }
        self.errors: List[str] = []

    def subscribe(self, event: HookEvent, callback: HookCallback) -> None:
        """Register a callback for a specific lifecycle event."""
        with self._lock:
            self._listeners[event].append(callback)

    def subscribe_all(self, callback: HookCallback) -> None:
        """Register a callback for every lifecycle event."""
        with self._lock:
            for event in HookEvent:
                self._listeners[event].append(callback)

    def emit(self, event: HookEvent, payload: Dict[str, Any]) -> None:
        """Dispatch an event to all registered callbacks."""
        with self._lock:
            listeners = list(self._listeners[event])
        for callback in listeners:
            try:
                callback(event, dict(payload))
            except Exception as exc:  # noqa: BLE001
                msg = f"Hook error on {event.value}: {type(exc).__name__}: {exc}"
                with self._lock:
                    self.errors.append(msg)
                if self.strict:
                    raise HookError(msg) from exc

    def listener_count(self, event: HookEvent) -> int:
        """Return the number of listeners registered for an event."""
        with self._lock:
            return len(self._listeners[event])


@dataclass
class AuditLogHook:
    """Thread-safe built-in hook that records a structured chronological log of events."""

    events: List[Dict[str, Any]] = field(default_factory=list)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def __call__(self, event: HookEvent, payload: Dict[str, Any]) -> None:
        with self._lock:
            self.events.append(
                {
                    "timestamp": time.time(),
                    "event": event.value,
                    "payload": dict(payload),
                }
            )

    def events_for_task(self, task_name: str) -> List[Dict[str, Any]]:
        """Filter recorded events pertaining to a specific task."""
        with self._lock:
            return [
                e for e in self.events if e["payload"].get("task_name") == task_name
            ]


@dataclass
class TimingHook:
    """Thread-safe built-in hook that tracks wall-clock start/end times per task."""

    _starts: Dict[str, float] = field(default_factory=dict)
    durations_ms: Dict[str, float] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def __call__(self, event: HookEvent, payload: Dict[str, Any]) -> None:
        task_name = payload.get("task_name")
        if not task_name:
            return
        with self._lock:
            if event == HookEvent.BEFORE_TASK:
                self._starts[task_name] = time.perf_counter()
            elif event == HookEvent.AFTER_TASK and task_name in self._starts:
                elapsed = (time.perf_counter() - self._starts.pop(task_name)) * 1000.0
                self.durations_ms[task_name] = round(elapsed, 3)
