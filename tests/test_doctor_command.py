"""Tests for the `ser-diff doctor` CLI command."""

from __future__ import annotations

from pathlib import Path

from serdiff import cli


def test_doctor_happy_path(tmp_path, capsys):
    exit_code = cli.main(["doctor", "--reports-dir", str(tmp_path)])

    captured = capsys.readouterr().out

    assert exit_code == cli.EXIT_SUCCESS
    assert "ser-diff version" in captured
    assert "Python version" in captured
    assert "Reports directory" in captured
    assert str(tmp_path) in captured
    assert "Doctor summary: All systems go." in captured


def test_doctor_reports_directory_not_writable(tmp_path, monkeypatch, capsys):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    original_access = cli.os.access

    def fake_access(path: str | Path, mode: int) -> bool:
        target = Path(path)
        if target == reports_dir:
            return False
        return original_access(path, mode)

    monkeypatch.setattr(cli.os, "access", fake_access)

    exit_code = cli.main(["doctor", "--reports-dir", str(reports_dir)])

    captured = capsys.readouterr().out

    assert exit_code == cli.EXIT_FAILURE
    assert "[FAIL] Reports directory" in captured
    assert "not writable" in captured
    assert "Issues detected" in captured
