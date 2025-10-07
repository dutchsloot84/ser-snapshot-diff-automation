"""Smoke test that the GUI module imports headlessly."""


def test_gui_import_smoke(monkeypatch):
    monkeypatch.setenv("SERDIFF_GUI_HEADLESS", "1")
    __import__("serdiff.gui_runner")
