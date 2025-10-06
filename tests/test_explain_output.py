from __future__ import annotations

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
    assert "Key fields:" in captured.out
    assert "Namespaces detected: yes" in captured.out
