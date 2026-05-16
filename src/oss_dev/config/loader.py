"""Configuration loader with layered TOML loading.

Loads config from system → user → project → env variables.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import tomli
from platformdirs import user_config_dir

from oss_dev.config.models import Config
from oss_dev.core.errors import ConfigError

CONFIG_FILE_NAME = "config.toml"


def get_config_dir() -> Path:
    return Path(user_config_dir("oss-dev"))


def get_system_config_path() -> Path:
    return get_config_dir() / CONFIG_FILE_NAME


def _parse_toml(path: Path) -> dict[str, Any]:
    try:
        with open(path, "rb") as f:
            return tomli.load(f)
    except tomli.TOMLDecodeError as e:
        raise ConfigError(f"Invalid TOML in {path}: {e}", details={"config_file": str(path)}) from e
    except OSError as e:
        raise ConfigError(f"Failed to read config file {path}: {e}", details={"config_file": str(path)}) from e


def _get_project_config(cwd: Path) -> Optional[Path]:
    current = cwd.resolve()
    agent_dir = current / ".oss-dev"
    if agent_dir.is_dir():
        config_file = agent_dir / CONFIG_FILE_NAME
        if config_file.is_file():
            return config_file
    return None


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def load_config(cwd: Optional[Path] = None) -> Config:
    """Load configuration from layered sources."""
    cwd = cwd or Path.cwd()
    config_dict: dict[str, Any] = {}

    system_path = get_system_config_path()
    if system_path.is_file():
        try:
            config_dict = _parse_toml(system_path)
        except ConfigError:
            pass

    project_path = _get_project_config(cwd)
    if project_path:
        try:
            project_dict = _parse_toml(project_path)
            config_dict = _merge_dicts(config_dict, project_dict)
        except ConfigError:
            pass

    if "cwd" not in config_dict:
        config_dict["cwd"] = cwd

    try:
        return Config(**config_dict)
    except Exception as e:
        raise ConfigError(f"Invalid configuration: {e}") from e
