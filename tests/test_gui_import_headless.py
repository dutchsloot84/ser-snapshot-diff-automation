"""Ensure the GUI entrypoint imports without side effects."""


def test_gui_import_smoke(monkeypatch) -> None:  # pragma: no cover - import smoke
    """Importing the GUI runner should succeed even in headless mode."""

    monkeypatch.setenv("SERDIFF_GUI_HEADLESS", "1")
    __import__("serdiff.gui_runner")
