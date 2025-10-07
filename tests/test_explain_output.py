from __future__ import annotations

import json
from pathlib import Path

from serdiff import cli

FIXTURES = Path(__file__).parent / "fixtures"


def test_explain_prints_detection_details(tmp_path: Path, capsys) -> None:
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
            "explain",
            "--auto",
            "--explain",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == cli.EXIT_SUCCESS
    assert "Explain" in captured.out
    assert "Schema: SER" in captured.out
    assert "Primary key:" in captured.out
    assert "Namespaces detected: yes" in captured.out


def test_explain_subcommand_json(tmp_path: Path, capsys) -> None:
    before = FIXTURES / "SER_before_ns.xml"
    after = FIXTURES / "SER_after_ns.xml"

    exit_code = cli.main(
        [
            "explain",
            "--before",
            str(before),
            "--after",
            str(after),
            "--output-dir",
            str(tmp_path),
            "--out-prefix",
            "explain-json",
            "--auto",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == cli.EXIT_SUCCESS
    payload = json.loads(captured.out)
    assert payload["schema"] == "SER"
    assert payload["summary"]["total_before"] == 2
    assert payload["namespaces_detected"] is True
    assert payload["key_fields"][0] == "AccountNumber"
