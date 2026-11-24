"""Configuration loading helpers for TaskFlow."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Optional

from taskflow.models import ConfigError, WorkflowConfig


ENV_PREFIX = "TASKFLOW_"


def _parse_bool(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"Cannot interpret '{raw}' as a boolean.")


def load_config_from_dict(data: Mapping[str, Any]) -> WorkflowConfig:
    """Build a WorkflowConfig from a mapping, validating unknown keys."""
    allowed = {
        "max_workers",
        "fail_fast",
        "default_retries",
        "enable_cache",
        "cache_dir",
        "strict_hooks",
        "report_format",
    }
    unknown = set(data.keys()) - allowed
    if unknown:
        raise ConfigError(f"Unknown configuration keys: {', '.join(sorted(unknown))}")

    kwargs: dict[str, Any] = {}
    if "max_workers" in data:
        try:
            kwargs["max_workers"] = int(data["max_workers"])
        except (TypeError, ValueError) as exc:
            raise ConfigError("max_workers must be an integer.") from exc
    if "default_retries" in data:
        try:
            kwargs["default_retries"] = int(data["default_retries"])
        except (TypeError, ValueError) as exc:
            raise ConfigError("default_retries must be an integer.") from exc
    if "fail_fast" in data:
        kwargs["fail_fast"] = _parse_bool(data["fail_fast"])
    if "enable_cache" in data:
        kwargs["enable_cache"] = _parse_bool(data["enable_cache"])
    if "strict_hooks" in data:
        kwargs["strict_hooks"] = _parse_bool(data["strict_hooks"])
    if "cache_dir" in data and data["cache_dir"] is not None:
        kwargs["cache_dir"] = Path(str(data["cache_dir"]))
    if "report_format" in data:
        kwargs["report_format"] = str(data["report_format"])

    return WorkflowConfig(**kwargs)


def load_config_from_env(environ: Optional[Mapping[str, str]] = None) -> WorkflowConfig:
    """Build a WorkflowConfig from TASKFLOW_* environment variables."""
    env = environ if environ is not None else os.environ
    extracted: dict[str, Any] = {}
    mapping = {
        "MAX_WORKERS": "max_workers",
        "FAIL_FAST": "fail_fast",
        "DEFAULT_RETRIES": "default_retries",
        "ENABLE_CACHE": "enable_cache",
        "CACHE_DIR": "cache_dir",
        "STRICT_HOOKS": "strict_hooks",
        "REPORT_FORMAT": "report_format",
    }
    for suffix, key in mapping.items():
        env_key = f"{ENV_PREFIX}{suffix}"
        if env_key in env and env[env_key].strip():
            extracted[key] = env[env_key].strip()
    return load_config_from_dict(extracted)


def load_config(
    config_file: Optional[Path | str] = None,
    overrides: Optional[Mapping[str, Any]] = None,
) -> WorkflowConfig:
    """Load config by layering defaults -> JSON file -> env -> explicit overrides."""
    merged: dict[str, Any] = {}

    if config_file is not None:
        path = Path(config_file)
        if not path.exists():
            raise ConfigError(f"Configuration file not found: {path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Invalid JSON in config file {path}: {exc}") from exc
        if not isinstance(raw, dict):
            raise ConfigError("Config file root must be a JSON object.")
        merged.update(raw)

    env_cfg = load_config_from_env()
    for field_name in (
        "max_workers",
        "fail_fast",
        "default_retries",
        "enable_cache",
        "cache_dir",
        "strict_hooks",
        "report_format",
    ):
        env_key = f"{ENV_PREFIX}{field_name.upper()}"
        if env_key in os.environ and os.environ[env_key].strip():
            merged[field_name] = getattr(env_cfg, field_name)

    if overrides:
        merged.update(overrides)

    return load_config_from_dict(merged)
