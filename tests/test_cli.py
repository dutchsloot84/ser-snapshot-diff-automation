from __future__ import annotations

from pathlib import Path

from serdiff import cli
from serdiff.diff import diff_files
from serdiff.presets import get_preset


def write_xml(path: Path, body: str) -> Path:
    path.write_text(body.strip(), encoding="utf-8")
    return path


def test_cli_threshold_failure(tmp_path: Path) -> None:
    before = write_xml(
        tmp_path / "before.xml",
        """
        <SimpleExposureRates>
          <Rate>
            <PublicID>SER-UBER-NY</PublicID>
            <Partner>Uber</Partner>
            <State>NY</State>
            <AgeBand>Adult</AgeBand>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <Factor>1.10</Factor>
          </Rate>
        </SimpleExposureRates>
        """,
    )
    after = write_xml(
        tmp_path / "after.xml",
        """
        <SimpleExposureRates>
          <Rate>
            <PublicID>SER-UBER-NY</PublicID>
            <Partner>Uber</Partner>
            <State>NY</State>
            <AgeBand>Adult</AgeBand>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <Factor>1.10</Factor>
          </Rate>
          <Rate>
            <PublicID>SER-NEW-01</PublicID>
            <Partner>Uber</Partner>
            <State>CA</State>
            <AgeBand>Adult</AgeBand>
            <EffectiveDate>2023-05-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <Factor>1.30</Factor>
          </Rate>
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
        ]
    )

    assert exit_code == cli.EXIT_GATES_FAILED


def test_expected_partner_detection(tmp_path: Path) -> None:
    before = write_xml(
        tmp_path / "before.xml",
        """
        <SimpleExposureRates>
          <Rate>
            <PublicID>SER-UBER-NY</PublicID>
            <Partner>Uber</Partner>
            <State>NY</State>
            <AgeBand>Adult</AgeBand>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <Factor>1.10</Factor>
          </Rate>
        </SimpleExposureRates>
        """,
    )
    after = write_xml(
        tmp_path / "after.xml",
        """
        <SimpleExposureRates>
          <Rate>
            <PublicID>SER-UBER-NY</PublicID>
            <Partner>Uber</Partner>
            <State>NY</State>
            <AgeBand>Adult</AgeBand>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <Factor>1.10</Factor>
          </Rate>
          <Rate>
            <PublicID>SER-DOORDASH-01</PublicID>
            <Partner>DoorDash</Partner>
            <State>TX</State>
            <AgeBand>Adult</AgeBand>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <Factor>1.00</Factor>
          </Rate>
        </SimpleExposureRates>
        """,
    )

    preset = get_preset("SER")
    result = diff_files(
        Path(before),
        Path(after),
        preset.config,
        jira="TEST-1",
        expected_partners=["Uber"],
    )
    assert "DoorDash" in result.unexpected_partners
