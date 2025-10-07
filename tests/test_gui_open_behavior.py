from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import serdiff.gui_runner as gui_runner
from serdiff import gui_utils
from serdiff.entrypoints import DiffRunResult


class MessageCapture:
    def __init__(self) -> None:
        self.info: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.warning: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def showinfo(self, *args: Any, **kwargs: Any) -> None:
        self.info.append((args, kwargs))

    def showwarning(self, *args: Any, **kwargs: Any) -> None:
        self.warning.append((args, kwargs))

    def showerror(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - compatibility
        self.warning.append((args, kwargs))


class DummyStatus:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def show(self, message: str, *, kind: str = "info") -> None:
        self.calls.append((message, kind))


def test_open_path_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: list[str] = []

    def fake_startfile(path: str) -> None:
        captured.append(path)

    monkeypatch.setattr(gui_utils.sys, "platform", "win32")
    monkeypatch.setattr(gui_utils.os, "startfile", fake_startfile, raising=False)

    gui_utils.open_path(tmp_path)

    assert captured == [str(tmp_path.resolve())]


def test_open_path_unix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool = False) -> None:
        calls.append(cmd)
        assert check is False

    monkeypatch.setattr(gui_utils.sys, "platform", "linux")
    monkeypatch.setattr(gui_utils.subprocess, "run", fake_run)

    gui_utils.open_path(tmp_path)

    assert calls == [["xdg-open", str(tmp_path.resolve())]]


def test_handle_result_prefers_primary_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    primary = tmp_path / "SER_Diff_Report.html"
    primary.write_text("<html></html>", encoding="utf-8")

    result = DiffRunResult(
        exit_code=0,
        output_dir=tmp_path,
        primary_report=primary,
        json_path=None,
    )

    opened: list[Path] = []
    monkeypatch.setattr(gui_runner, "open_path", lambda target: opened.append(Path(target)))

    messages = MessageCapture()
    monkeypatch.setattr(gui_runner, "messagebox", messages)

    status = DummyStatus()
    gui_runner._handle_result(result, status)

    assert opened == [primary]
    assert status.calls[-1] == ("Reports created", "info")
    assert messages.warning == []
    assert messages.info, "Expected completion dialog"


def test_handle_result_falls_back_to_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()

    result = DiffRunResult(
        exit_code=0,
        output_dir=output_dir,
        primary_report=None,
        json_path=None,
    )

    opened: list[Path] = []
    monkeypatch.setattr(gui_runner, "open_path", lambda target: opened.append(Path(target)))

    messages = MessageCapture()
    monkeypatch.setattr(gui_runner, "messagebox", messages)

    status = DummyStatus()
    gui_runner._handle_result(result, status)

    assert opened == [output_dir]
    assert status.calls[-1] == ("Reports created", "info")
    assert messages.warning == []
    assert messages.info, "Expected completion dialog"


def test_handle_result_warns_when_nothing_to_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing_report = tmp_path / "missing" / "SER_Diff_Report.html"
    result = DiffRunResult(
        exit_code=0,
        output_dir=tmp_path / "other-missing",
        primary_report=missing_report,
        json_path=None,
    )

    def fail_open(_target: Path) -> None:  # pragma: no cover - should not be invoked
        raise AssertionError("open_path should not be called")

    monkeypatch.setattr(gui_runner, "open_path", fail_open)

    messages = MessageCapture()
    monkeypatch.setattr(gui_runner, "messagebox", messages)

    status = DummyStatus()
    gui_runner._handle_result(result, status)

    assert messages.warning, "Expected warning when report could not be opened"
    assert any("Could not open report" in args[0] for args, _ in messages.warning)
    assert messages.info, "Expected completion dialog"
    assert status.calls[-1] == ("Reports created", "info")
