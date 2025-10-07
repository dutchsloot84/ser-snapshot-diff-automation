from __future__ import annotations

from pathlib import Path

from serdiff.entrypoints import run_diff

FIXTURE_DIR = Path(__file__).parent / "fixtures"
BEFORE = FIXTURE_DIR / "SER_before_ns.xml"
AFTER = FIXTURE_DIR / "SER_after_ns.xml"


def test_run_diff_returns_html_paths(tmp_path: Path) -> None:
    result = run_diff(
        before=BEFORE,
        after=AFTER,
        report="html",
        output_dir=tmp_path / "reports",
    )

    assert result.output_dir.is_dir()
    assert result.primary_report is not None
    assert result.primary_report.suffix == ".html"
    assert result.primary_report.exists()
    assert result.primary_report.parent == result.output_dir
    assert result.json_path is not None and result.json_path.exists()
    assert all(path.exists() for path in result.extra_reports)


def test_run_diff_returns_xlsx_paths(tmp_path: Path) -> None:
    result = run_diff(
        before=BEFORE,
        after=AFTER,
        report="xlsx",
        output_dir=tmp_path / "reports",
    )

    assert result.output_dir.is_dir()
    assert result.primary_report is not None
    assert result.primary_report.suffix == ".xlsx"
    assert result.primary_report.exists()
    assert result.primary_report.parent == result.output_dir
    assert result.json_path is not None and result.json_path.exists()
    assert all(path.exists() for path in result.extra_reports)
