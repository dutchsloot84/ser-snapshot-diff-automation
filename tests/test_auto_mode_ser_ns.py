from __future__ import annotations

import json
from pathlib import Path

from serdiff import cli

FIXTURES = Path(__file__).parent / "fixtures"


def test_auto_mode_handles_namespaced_ser(tmp_path: Path, capsys) -> None:
    before = FIXTURES / "SER_before_ns.xml"
    after = FIXTURES / "SER_after_ns.xml"

    exit_code = cli.main(
        [
            "--before",
            str(before),
            "--after",
            str(after),
            "--output-dir",
            str(tmp_path),
            "--out-prefix",
            "auto-ser",
            "--auto",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == cli.EXIT_SUCCESS
    assert "Diff: added=1" in captured.out

    report = tmp_path / "auto-ser.json"
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["summary"]["total_before"] == 2
    assert data["summary"]["total_after"] == 2
    assert data["summary"]["added"] == 1
    assert data["summary"]["removed"] == 1
    assert data["meta"]["schema"] == "SER"
    assert data["meta"]["namespace_detected"] is True
    assert data["meta"]["key_fields_used"][0] == "AccountNumber"
