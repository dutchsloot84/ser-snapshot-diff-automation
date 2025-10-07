"""Utilities shared by the Tkinter GUI runner."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - fallback for Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

STATE_DIR = Path.home() / ".serdiff_gui"
STATE_PATH = STATE_DIR / "state.json"


def open_folder(path: str | Path) -> None:
    """Open *path* with the system file explorer."""

    resolved = str(Path(path).expanduser().resolve())
    if sys.platform.startswith("win"):
        os.startfile(resolved)  # noqa: S606 - deliberate shell interaction
    elif sys.platform == "darwin":
        subprocess.run(["open", resolved], check=False)
    else:
        subprocess.run(["xdg-open", resolved], check=False)


def get_default_output_dir(stamp: str | None = None) -> Path:
    """Return (and create) the default reports directory under ``~/SER-Diff-Reports``."""

    from datetime import datetime

    timestamp = stamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    target = Path.home() / "SER-Diff-Reports" / timestamp
    target.mkdir(parents=True, exist_ok=True)
    return target


def _load_yaml(path: Path) -> dict[str, Any] | None:
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None


def load_prefill_jira_ticket(base_dir: Path | None = None) -> str | None:
    """Return the Jira ticket from ``.serdiff.*`` if available."""

    base = base_dir or Path.cwd()

    toml_path = base / ".serdiff.toml"
    if toml_path.exists():
        try:
            data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
            ticket = (data.get("jira") or {}).get("ticket")
            if isinstance(ticket, str) and ticket.strip():
                return ticket.strip()
        except Exception:
            return None

    for candidate in (".serdiff.yaml", ".serdiff.yml"):
        yaml_path = base / candidate
        if yaml_path.exists():
            data = _load_yaml(yaml_path)
            if isinstance(data, dict):
                ticket = (data.get("jira") or {}).get("ticket")
                if isinstance(ticket, str) and ticket.strip():
                    return ticket.strip()
            return None

    json_path = base / ".serdiff.json"
    if json_path.exists():
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            ticket = (payload.get("jira") or {}).get("ticket")
            if isinstance(ticket, str) and ticket.strip():
                return ticket.strip()
        except Exception:
            return None

    return None


def load_state() -> dict[str, Any]:
    """Load persisted GUI state from disk."""

    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def save_state(data: dict[str, Any]) -> None:
    """Persist GUI state to disk."""

    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        pass


def get_last_directory() -> Path | None:
    """Return the last directory used in the GUI, if available."""

    state = load_state()
    last = state.get("last_directory")
    if isinstance(last, str) and last.strip():
        path = Path(last).expanduser()
        if path.exists():
            return path
    return None


def remember_last_directory(path: str | Path) -> None:
    """Persist the parent directory of *path* for the next session."""

    directory = Path(path).expanduser()
    if directory.is_file():
        directory = directory.parent
    state = load_state()
    state["last_directory"] = str(directory.resolve())
    save_state(state)


__all__ = [
    "STATE_PATH",
    "open_folder",
    "get_default_output_dir",
    "load_prefill_jira_ticket",
    "load_state",
    "save_state",
    "get_last_directory",
    "remember_last_directory",
]
