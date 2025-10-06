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
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <ExposureType>Auto</ExposureType>
            <RateEffectiveDate>2023-01-01</RateEffectiveDate>
            <RatingExposureType>Primary</RatingExposureType>
            <Segment>SegmentB</Segment>
            <State>CA</State>
            <Value>0.95</Value>
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
            <Value>1.20</Value>
          </CASSimpleExpsRateTbl_Ext>
          <CASSimpleExpsRateTbl_Ext>
            <AccountNumber>ACC-003</AccountNumber>
            <CovFactor>1.00</CovFactor>
            <EffectiveDate>2023-06-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <ExposureType>Auto</ExposureType>
            <RateEffectiveDate>2023-06-01</RateEffectiveDate>
            <RatingExposureType>Primary</RatingExposureType>
            <Segment>SegmentC</Segment>
            <State>IL</State>
            <Value>1.40</Value>
          </CASSimpleExpsRateTbl_Ext>
        </SimpleExposureRates>
        """,
    )

    result = diff_files(before, after, ser_config)

    assert result.summary["added"] == 1
    assert result.summary["removed"] == 1
    assert result.summary["updated"] == 1
    assert result.meta["schema"] == "SER"
    assert result.meta["duplicates_resolved"]["resolved"] is True
    assert result.meta["key_fields_used"] == [
        "AccountNumber",
        "CovFactor",
        "ExposureType",
        "RatingExposureType",
        "Segment",
        "State",
        "EffectiveDate",
        "RateEffectiveDate",
        "ExpirationDate",
    ]
    updated = result.updated[0]
    assert "AccountNumber=ACC-001" in updated["key"]
    assert updated["changes"]["Value"] == {"before": "1.10", "after": "1.20"}


def test_composite_key_support(tmp_path: Path, ser_config: DiffConfig) -> None:
    before = write_xml(
        tmp_path / "before.xml",
        """
        <SimpleExposureRates>
          <CASSimpleExpsRateTbl_Ext>
            <AccountNumber>ACC-010</AccountNumber>
            <CovFactor>2.00</CovFactor>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <ExposureType>Auto</ExposureType>
            <RateEffectiveDate>2023-01-01</RateEffectiveDate>
            <RatingExposureType>Primary</RatingExposureType>
            <Segment>SegmentZ</Segment>
            <State>WA</State>
            <Value>1.00</Value>
          </CASSimpleExpsRateTbl_Ext>
        </SimpleExposureRates>
        """,
    )
    after = write_xml(
        tmp_path / "after.xml",
        """
        <SimpleExposureRates>
          <CASSimpleExpsRateTbl_Ext>
            <AccountNumber>ACC-010</AccountNumber>
            <CovFactor>2.00</CovFactor>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <ExposureType>Auto</ExposureType>
            <RateEffectiveDate>2023-01-01</RateEffectiveDate>
            <RatingExposureType>Primary</RatingExposureType>
            <Segment>SegmentZ</Segment>
            <State>WA</State>
            <Value>1.05</Value>
          </CASSimpleExpsRateTbl_Ext>
        </SimpleExposureRates>
        """,
    )

    result = diff_files(before, after, ser_config)
    assert result.summary["updated"] == 1
    assert result.updated[0]["key"].startswith("AccountNumber=ACC-010")
    assert result.meta["key_fields_used"] == [
        "AccountNumber",
        "CovFactor",
        "ExposureType",
        "RatingExposureType",
        "Segment",
        "State",
        "EffectiveDate",
        "RateEffectiveDate",
        "ExpirationDate",
    ]


def test_whitespace_normalisation(tmp_path: Path, ser_config: DiffConfig) -> None:
    before = write_xml(
        tmp_path / "before.xml",
        """
        <SimpleExposureRates>
          <CASSimpleExpsRateTbl_Ext>
            <AccountNumber> ACC-001 </AccountNumber>
            <CovFactor> 1.00 </CovFactor>
            <EffectiveDate> 2023-01-01 </EffectiveDate>
            <ExpirationDate> 2023-12-31 </ExpirationDate>
            <ExposureType> Auto </ExposureType>
            <RateEffectiveDate> 2023-01-01 </RateEffectiveDate>
            <RatingExposureType> Primary </RatingExposureType>
            <Segment> SegmentA </Segment>
            <State> NY </State>
            <Value> 1.10 </Value>
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
        </SimpleExposureRates>
        """,
    )

    result = diff_files(before, after, ser_config)
    assert result.summary["updated"] == 0
    assert result.meta["namespace_detected"] is False
