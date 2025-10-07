from __future__ import annotations

import types
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from serdiff import gui_utils


class DummyVar:
    def __init__(self, value: str = "", **_: Any) -> None:
        self._value = value
        self._callbacks: list[Callable[[str, str, str], None]] = []

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value
        for callback in self._callbacks:
            callback("", "", "")

    def trace_add(self, _mode: str, callback: Callable[[str, str, str], None]) -> None:
        self._callbacks.append(callback)


class DummyWidget:
    def __init__(self, *_: Any, **__: Any) -> None:
        self.config_calls: list[dict[str, Any]] = []

    def pack(self, **__: Any) -> DummyWidget:
        return self

    def config(self, **kwargs: Any) -> None:
        self.config_calls.append(kwargs)


class DummyTk(DummyWidget):
    def __init__(self, *_: Any, **__: Any) -> None:
        super().__init__()
        self.children: list[DummyWidget] = []

    def title(self, *_: Any) -> None:  # pragma: no cover - simple stub
        pass

    def resizable(self, *_: Any) -> None:  # pragma: no cover - simple stub
        pass

    def update_idletasks(self) -> None:  # pragma: no cover - simple stub
        pass

    def destroy(self) -> None:  # pragma: no cover - simple stub
        pass

    def mainloop(self) -> None:  # pragma: no cover - simple stub
        pass


class DummyButton(DummyWidget):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.command: Callable[..., Any] | None = kwargs.get("command")
        self.state = kwargs.get("state")

    def config(self, **kwargs: Any) -> None:
        if "command" in kwargs:
            self.command = kwargs["command"]
        if "state" in kwargs:
            self.state = kwargs["state"]
        super().config(**kwargs)


class DummyFrame(DummyWidget):
    pass


class DummyEntry(DummyWidget):
    pass


class DummyLabel(DummyWidget):
    pass


class DummyFileDialog:
    @staticmethod
    def askopenfilename(**__: Any) -> str:
        return ""


class DummyMessageBox:
    @staticmethod
    def showinfo(*_: Any, **__: Any) -> None:
        pass

    @staticmethod
    def showwarning(*_: Any, **__: Any) -> None:
        pass

    @staticmethod
    def showerror(*_: Any, **__: Any) -> None:
        pass


def test_load_prefill_from_toml(tmp_path: Path) -> None:
    config = tmp_path / ".serdiff.toml"
    config.write_text("""[jira]\nticket = \"ENG-123\"\n""", encoding="utf-8")

    assert gui_utils.load_prefill_jira_ticket(tmp_path) == "ENG-123"


def test_gui_runner_headless(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERDIFF_GUI_HEADLESS", "1")
    import serdiff.gui_runner as gui_runner

    dummy_tk_module = types.SimpleNamespace(
        Tk=DummyTk,
        Frame=DummyFrame,
        Button=DummyButton,
        Entry=DummyEntry,
        Label=DummyLabel,
        StringVar=DummyVar,
        X="x",
        LEFT="left",
        RIGHT="right",
        NORMAL="normal",
        DISABLED="disabled",
    )

    monkeypatch.setattr(gui_runner, "tk", dummy_tk_module)
    monkeypatch.setattr(gui_runner, "filedialog", DummyFileDialog)
    monkeypatch.setattr(gui_runner, "messagebox", DummyMessageBox)
    monkeypatch.setattr(
        gui_runner,
        "StatusBanner",
        type("DummyStatus", (DummyLabel,), {"show": lambda self, *_args, **_kwargs: None}),
    )
    monkeypatch.setattr(gui_runner, "get_default_output_dir", lambda: Path("/tmp/ser-diff"))
    monkeypatch.setattr(gui_runner, "run_diff", lambda **_: None)

    root = gui_runner.main()
    assert isinstance(root, DummyTk)
