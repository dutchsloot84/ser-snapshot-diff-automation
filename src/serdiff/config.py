"""Configuration loading helpers for ser-diff."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:  # pragma: no cover - fallback for Python < 3.11
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - fallback import
    import tomli as tomllib  # type: ignore[no-redef]

import yaml

CONFIG_FILENAMES = [".serdiff.toml", ".serdiff.yaml", ".serdiff.yml", ".serdiff.json"]


@dataclass(slots=True)
class LoadedConfig:
    """Container for a configuration file discovered on disk."""

    path: Path | None
    data: dict[str, Any]

    @property
    def exists(self) -> bool:
        return self.path is not None


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError("YAML configuration must be a mapping at the top level")
    return loaded


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError("JSON configuration must be a mapping at the top level")
    return loaded


def load_config(base_dir: Path | None = None) -> LoadedConfig:
    """Load configuration from disk using precedence TOML > YAML > JSON."""

    search_root = base_dir or Path.cwd()

    for name in CONFIG_FILENAMES:
        candidate = search_root / name
        if not candidate.exists():
            continue
        if candidate.suffix == ".toml":
            data = _load_toml(candidate)
        elif candidate.suffix in {".yaml", ".yml"}:
            data = _load_yaml(candidate)
        else:
            data = _load_json(candidate)
        if not isinstance(data, dict):
            raise ValueError("Configuration must be a mapping at the top level")
        return LoadedConfig(path=candidate, data=data)

    return LoadedConfig(path=None, data={})

