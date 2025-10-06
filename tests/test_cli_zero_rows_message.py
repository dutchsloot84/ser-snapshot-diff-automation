from __future__ import annotations

from pathlib import Path

import pytest

from serdiff import cli


def _write(path: Path, xml: str) -> Path:
    path.write_text(xml.strip(), encoding="utf-8")
    return path


@pytest.mark.usefixtures("tmp_path")
def test_cli_warns_when_no_records(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    before = _write(
        tmp_path / "before.xml",
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
        """,
    )
    after = _write(tmp_path / "after.xml", before.read_text(encoding="utf-8"))

    exit_code = cli.main(
        [
            "--before",
            str(before),
            "--after",
            str(after),
            "--table",
            "SER",
            "--record-localname",
            "WrongElement",
            "--out-prefix",
            str(tmp_path / "report"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == cli.EXIT_SUCCESS
    assert "No records parsed from BEFORE" in captured.err
    assert "No records parsed from AFTER" in captured.err
    assert "--strip-ns" in captured.err
