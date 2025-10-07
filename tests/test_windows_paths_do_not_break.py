from __future__ import annotations

from pathlib import Path

from serdiff import cli


def test_windows_style_output_dir(tmp_path: Path, capsys, monkeypatch) -> None:
    before = tmp_path / "before.xml"
    before.write_text(
        """
        <SimpleExposureRates>
          <CASSimpleExpsRateTbl_Ext>
            <AccountNumber>ACC-001</AccountNumber>
            <CovFactor>1.00</CovFactor>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <ExposureType>Auto</ExposureType>
            <RateEffectiveDate>2023-01-01</RateEffectiveDate>
            <RatingExposureType>Primary</RatingExposureType>
            <Segment>SegmentA</Segment>
            <State>NY</State>
            <Value>1.10</Value>
          </CASSimpleExpsRateTbl_Ext>
        </SimpleExposureRates>
        """.strip(),
        encoding="utf-8",
    )
    after = tmp_path / "after.xml"
    after.write_text(before.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    windows_output = "reports\\windows"

    exit_code = cli.main(
        [
            "--before",
            str(before.name),
            "--after",
            str(after.name),
            "--table",
            "SER",
            "--output-dir",
            windows_output,
            "--out-prefix",
            "win",  # prefix inside the windows-style directory
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == cli.EXIT_SUCCESS
    assert "reports\\windows" in captured.out
    output_dir = Path("reports\\windows")
    assert output_dir.exists()
    report_root = output_dir / "win"
    assert report_root.exists()
    assert (report_root / "diff.json").exists()
