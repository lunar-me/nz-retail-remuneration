"""Configuration loading and validation for the programme.

Loads YAML configuration files (e.g. ``configs/synthetic_data.yaml``) and
exposes them as a typed, validated structure. All generators and engines
consume configuration through this module so assumptions live in one place.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

# Root of the repository (two levels up from this file: src/common/config.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "configs"


class ConfigError(Exception):
    """Raised when a configuration file is missing or invalid."""


def load_yaml(path: Path | str) -> Dict[str, Any]:
    """Load a YAML file and return its contents as a dict.

    Parameters
    ----------
    path : Path | str
        Path to the YAML file. Relative paths are resolved against the
        repository ``configs/`` directory.

    Returns
    -------
    Dict[str, Any]
        Parsed YAML content.

    Raises
    ------
    ConfigError
        If the file does not exist or cannot be parsed.
    """
    p = Path(path)
    if not p.is_absolute():
        p = CONFIG_DIR / p

    if not p.exists():
        raise ConfigError(f"Configuration file not found: {p}")

    try:
        with p.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse YAML in {p}: {exc}") from exc


def load_synthetic_data_config(path: Path | str = "synthetic_data.yaml") -> Dict[str, Any]:
    """Load the synthetic data generation configuration.

    Parameters
    ----------
    path : Path | str, optional
        Path to the synthetic data YAML config (default ``synthetic_data.yaml``).

    Returns
    -------
    Dict[str, Any]
        The parsed configuration dictionary.
    """
    return load_yaml(path)