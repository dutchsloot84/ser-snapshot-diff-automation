"""Ensure GUI modules are importable without package hacks."""


def test_import_gui_runner():
    module = __import__("serdiff.gui_runner", fromlist=["gui_runner"])
    assert hasattr(module, "main")


def test_import_gui_utils():
    module = __import__("serdiff.gui_utils", fromlist=["gui_utils"])
    assert hasattr(module, "open_path")
