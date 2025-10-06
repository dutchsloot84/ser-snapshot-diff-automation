from __future__ import annotations

import json
from pathlib import Path

from serdiff import cli


def _write(path: Path, xml: str) -> Path:
    path.write_text(xml.strip(), encoding="utf-8")
    return path


def test_auto_mode_extends_key_for_duplicates(tmp_path: Path, capsys) -> None:
    before = _write(
        tmp_path / "before.xml",
        """
        <SimpleExposureRates>
          <CASSimpleExpsRateTbl_Ext>
            <AccountNumber>ACC-900</AccountNumber>
            <CovFactor>1.00</CovFactor>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <ExposureType>Auto</ExposureType>
            <RateEffectiveDate>2023-01-01</RateEffectiveDate>
            <RatingExposureType>Primary</RatingExposureType>
            <Segment>SegmentX</Segment>
            <State>NY</State>
            <Value>1.10</Value>
          </CASSimpleExpsRateTbl_Ext>
          <CASSimpleExpsRateTbl_Ext>
            <AccountNumber>ACC-900</AccountNumber>
            <CovFactor>1.00</CovFactor>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <ExposureType>Auto</ExposureType>
            <RateEffectiveDate>2023-01-01</RateEffectiveDate>
            <RatingExposureType>Primary</RatingExposureType>
            <Segment>SegmentX</Segment>
            <State>NY</State>
            <Value>1.20</Value>
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
            "--output-dir",
            str(tmp_path),
            "--out-prefix",
            "auto-dup",
            "--auto",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == cli.EXIT_SUCCESS
    assert "Diff: added=0" in captured.out

    report = tmp_path / "auto-dup.json"
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["summary"]["total_before"] == 2
    assert data["meta"]["duplicates_resolved"]["resolved"] is True
    assert "Value" in data["meta"]["key_fields_used"]
