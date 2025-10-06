from __future__ import annotations

from pathlib import Path

import pytest

from serdiff.diff import DiffConfig, diff_files
from serdiff.presets import get_preset


@pytest.fixture
def ser_config() -> DiffConfig:
    return get_preset("SER").config


def write_xml(path: Path, body: str) -> Path:
    path.write_text(body.strip(), encoding="utf-8")
    return path


def test_ser_diff_add_remove_update(tmp_path: Path, ser_config: DiffConfig) -> None:
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
          <Rate>
            <PublicID>SER-HELLO-CA</PublicID>
            <Partner>HelloFresh</Partner>
            <State>CA</State>
            <AgeBand>Adult</AgeBand>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <Factor>0.95</Factor>
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
            <Factor>1.20</Factor>
          </Rate>
          <Rate>
            <PublicID>SER-MARSH-IL</PublicID>
            <Partner>Marsh Risk</Partner>
            <State>IL</State>
            <AgeBand>Adult</AgeBand>
            <EffectiveDate>2023-06-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <Factor>1.40</Factor>
          </Rate>
        </SimpleExposureRates>
        """,
    )

    result = diff_files(before, after, ser_config)

    assert result.summary["added"] == 1
    assert result.summary["removed"] == 1
    assert result.summary["updated"] == 1
    updated = result.updated[0]
    assert updated["key"] == "PublicID=SER-UBER-NY"
    assert updated["changes"]["Factor"] == {"before": "1.10", "after": "1.20"}


def test_composite_key_support(tmp_path: Path, ser_config: DiffConfig) -> None:
    before = write_xml(
        tmp_path / "before.xml",
        """
        <SimpleExposureRates>
          <Rate>
            <Partner>Uber</Partner>
            <State>WA</State>
            <AgeBand>Adult</AgeBand>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <Factor>1.00</Factor>
          </Rate>
        </SimpleExposureRates>
        """,
    )
    after = write_xml(
        tmp_path / "after.xml",
        """
        <SimpleExposureRates>
          <Rate>
            <Partner>Uber</Partner>
            <State>WA</State>
            <AgeBand>Adult</AgeBand>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <Factor>1.05</Factor>
          </Rate>
        </SimpleExposureRates>
        """,
    )

    result = diff_files(before, after, ser_config)
    assert result.summary["updated"] == 1
    assert result.updated[0]["key"].startswith("Partner=Uber")


def test_whitespace_normalisation(tmp_path: Path, ser_config: DiffConfig) -> None:
    before = write_xml(
        tmp_path / "before.xml",
        """
        <SimpleExposureRates>
          <Rate>
            <PublicID>SER-UBER-NY</PublicID>
            <Partner> Uber </Partner>
            <State> NY </State>
            <AgeBand>Adult</AgeBand>
            <EffectiveDate> 2023-01-01 </EffectiveDate>
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
        </SimpleExposureRates>
        """,
    )

    result = diff_files(before, after, ser_config)
    assert result.summary["updated"] == 0
