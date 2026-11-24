"""Command handler registry and built-in workflow commands."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Iterable, List, Optional

TaskHandler = Callable[[Dict[str, Any], Dict[str, Any]], Any]


class CommandRegistry:
    """Stores named command handlers, optional aliases, and documentation."""

    def __init__(self, initial: Optional[Dict[str, TaskHandler]] = None) -> None:
        self._handlers: Dict[str, TaskHandler] = {}
        self._aliases: Dict[str, str] = {}
        self._docs: Dict[str, str] = {}
        if initial:
            for name, fn in initial.items():
                self.register(name, fn)

    def register(
        self,
        name: str,
        handler: TaskHandler,
        description: str = "",
        aliases: Optional[Iterable[str]] = None,
    ) -> None:
        """Register a command handler under `name` and optional aliases."""
        if not name or not name.strip():
            raise ValueError("Command name must be non-empty.")
        self._handlers[name] = handler
        if description:
            self._docs[name] = description
        if aliases:
            for alias in aliases:
                self._aliases[alias] = name

    def resolve_name(self, name: str) -> str:
        """Resolve an alias to its canonical command name."""
        return self._aliases.get(name, name)

    def get(self, name: str) -> Optional[TaskHandler]:
        """Return the registered handler for `name` (or alias), or None."""
        canonical = self.resolve_name(name)
        return self._handlers.get(canonical)

    def has(self, name: str) -> bool:
        """Return True if a command name or alias is registered."""
        return self.get(name) is not None

    def list_commands(self) -> List[str]:
        """Return sorted canonical command names."""
        return sorted(self._handlers.keys())

    def describe(self, name: str) -> str:
        """Return documentation string for a command, if available."""
        canonical = self.resolve_name(name)
        return self._docs.get(canonical, "")

    def as_dict(self) -> Dict[str, TaskHandler]:
        """Return a plain mapping including aliases for compatibility."""
        merged = dict(self._handlers)
        for alias, target in self._aliases.items():
            if target in self._handlers:
                merged[alias] = self._handlers[target]
        return merged


def build_default_registry() -> Dict[str, TaskHandler]:
    """Provide built-in demo command handlers for CLI and test workflows."""

    def cmd_echo(params: Dict[str, Any], upstream: Dict[str, Any]) -> str:
        return str(params.get("message", ""))

    def cmd_upper(params: Dict[str, Any], upstream: Dict[str, Any]) -> str:
        source_key = params.get("from")
        text = (
            str(upstream[source_key])
            if source_key in upstream
            else str(params.get("text", ""))
        )
        return text.upper()

    def cmd_lower(params: Dict[str, Any], upstream: Dict[str, Any]) -> str:
        source_key = params.get("from")
        text = (
            str(upstream[source_key])
            if source_key in upstream
            else str(params.get("text", ""))
        )
        return text.lower()

    def cmd_concat(params: Dict[str, Any], upstream: Dict[str, Any]) -> str:
        sep = str(params.get("sep", " "))
        values = [str(upstream[k]) for k in sorted(upstream)]
        return sep.join(values)

    def cmd_word_count(params: Dict[str, Any], upstream: Dict[str, Any]) -> int:
        combined = " ".join(str(v) for v in upstream.values())
        return len(combined.split())

    def cmd_sum_numbers(params: Dict[str, Any], upstream: Dict[str, Any]) -> float:
        base = float(params.get("base", 0))
        total = base + sum(float(v) for v in upstream.values())
        return total

    def cmd_template(params: Dict[str, Any], upstream: Dict[str, Any]) -> str:
        fmt = str(params.get("template", "{value}"))
        ctx = dict(params)
        ctx.update(upstream)
        return fmt.format(**ctx)

    def cmd_sleep_ms(params: Dict[str, Any], upstream: Dict[str, Any]) -> str:
        ms = float(params.get("ms", 1))
        time.sleep(max(0.0, ms / 1000.0))
        return str(params.get("label", "done"))

    reg = CommandRegistry()
    reg.register("echo", cmd_echo, "Emit a static message string.")
    reg.register("upper", cmd_upper, "Convert upstream or param text to uppercase.")
    reg.register("lower", cmd_lower, "Convert upstream or param text to lowercase.")
    reg.register("concat", cmd_concat, "Join sorted upstream values with a separator.")
    reg.register("word_count", cmd_word_count, "Count whitespace-delimited words in upstream outputs.")
    reg.register("sum_numbers", cmd_sum_numbers, "Sum numeric upstream outputs plus an optional base.")
    reg.register("template", cmd_template, "Format a Python template string with params and upstream values.")
    reg.register("sleep_ms", cmd_sleep_ms, "Sleep for a given number of milliseconds (for latency tests).")
    return reg.as_dict()
