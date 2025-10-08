"""Smoke tests for CLI importability."""


def test_cli_import_smoke() -> None:
    """Importing the CLI module should succeed without relative imports."""

    __import__("serdiff.cli")
