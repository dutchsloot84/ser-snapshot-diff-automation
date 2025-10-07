from __future__ import annotations

from pathlib import Path

from serdiff import cli
from serdiff.diff import diff_files
from serdiff.presets import get_preset


def write_xml(path: Path, body: str) -> Path:
    path.write_text(body.strip(), encoding="utf-8")
    return path


def test_cli_threshold_failure(tmp_path: Path, capsys) -> None:
    before = write_xml(
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
    after = write_xml(
        tmp_path / "after.xml",
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
          <CASSimpleExpsRateTbl_Ext>
            <AccountNumber>ACC-002</AccountNumber>
            <CovFactor>1.00</CovFactor>
            <EffectiveDate>2023-05-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <ExposureType>Auto</ExposureType>
            <RateEffectiveDate>2023-05-01</RateEffectiveDate>
            <RatingExposureType>Primary</RatingExposureType>
            <Segment>SegmentB</Segment>
            <State>CA</State>
            <Value>1.30</Value>
          </CASSimpleExpsRateTbl_Ext>
        </SimpleExposureRates>
        """,
    )

    exit_code = cli.main(
        [
            "--before",
            str(before),
            "--after",
            str(after),
            "--table",
            "SER",
            "--max-added",
            "0",
            "--fail-on-unexpected",
            "--output-dir",
            str(tmp_path),
            "--out-prefix",
            "report",
            "--report",
            "html",
        ]
    )

    assert exit_code == cli.EXIT_GATES_FAILED
    captured = capsys.readouterr()
    assert "Diff summary | added:" in captured.out
    assert "Warning:" in captured.err

    report_dir = tmp_path / "report"
    assert (report_dir / "diff.json").exists()
    assert any(path.suffix == ".html" for path in report_dir.iterdir())


def test_expected_partner_detection(tmp_path: Path) -> None:
    before = write_xml(
        tmp_path / "before.xml",
        """
        <ExposureTypes>
          <ExposureType>
            <PublicID>EXP-001</PublicID>
            <ExposureCode>AUTO</ExposureCode>
            <Partner>Uber</Partner>
            <State>NY</State>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
          </ExposureType>
        </ExposureTypes>
        """,
    )
    after = write_xml(
        tmp_path / "after.xml",
        """
        <ExposureTypes>
          <ExposureType>
            <PublicID>EXP-001</PublicID>
            <ExposureCode>AUTO</ExposureCode>
            <Partner>Uber</Partner>
            <State>NY</State>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
          </ExposureType>
          <ExposureType>
            <PublicID>EXP-002</PublicID>
            <ExposureCode>AUTO</ExposureCode>
            <Partner>DoorDash</Partner>
            <State>TX</State>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
          </ExposureType>
        </ExposureTypes>
        """,
    )

    preset = get_preset("EXPOSURE")
    result = diff_files(
        Path(before),
        Path(after),
        preset.config,
        jira="TEST-1",
        expected_partners=["Uber"],
    )
    assert "DoorDash" in result.unexpected_partners
