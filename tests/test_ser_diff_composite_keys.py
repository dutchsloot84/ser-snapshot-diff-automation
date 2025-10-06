from __future__ import annotations

from pathlib import Path

from serdiff.diff import diff_files
from serdiff.presets import get_preset


def _write(path: Path, xml: str) -> Path:
    path.write_text(xml.strip(), encoding="utf-8")
    return path


def test_composite_key_diff_is_order_agnostic(tmp_path: Path) -> None:
    config = get_preset("SER").config

    before = _write(
        tmp_path / "before.xml",
        """
        <SimpleExposureRates>
          <CASSimpleExpsRateTbl_Ext>
            <AccountNumber>ACC-100</AccountNumber>
            <CovFactor>1.00</CovFactor>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <ExposureType>Auto</ExposureType>
            <RateEffectiveDate>2023-01-01</RateEffectiveDate>
            <RatingExposureType>Primary</RatingExposureType>
            <Segment>SegmentA</Segment>
            <State>CA</State>
            <Value>1.10</Value>
          </CASSimpleExpsRateTbl_Ext>
          <CASSimpleExpsRateTbl_Ext>
            <AccountNumber>ACC-200</AccountNumber>
            <CovFactor>2.00</CovFactor>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <ExposureType>Auto</ExposureType>
            <RateEffectiveDate>2023-01-01</RateEffectiveDate>
            <RatingExposureType>Primary</RatingExposureType>
            <Segment>SegmentB</Segment>
            <State>WA</State>
            <Value>1.00</Value>
          </CASSimpleExpsRateTbl_Ext>
        </SimpleExposureRates>
        """,
    )

    after = _write(
        tmp_path / "after.xml",
        """
        <SimpleExposureRates>
          <CASSimpleExpsRateTbl_Ext>
            <AccountNumber>ACC-200</AccountNumber>
            <CovFactor>2.00</CovFactor>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <ExposureType>Auto</ExposureType>
            <RateEffectiveDate>2023-01-01</RateEffectiveDate>
            <RatingExposureType>Primary</RatingExposureType>
            <Segment>SegmentB</Segment>
            <State>WA</State>
            <Value>1.05</Value>
          </CASSimpleExpsRateTbl_Ext>
          <CASSimpleExpsRateTbl_Ext>
            <AccountNumber>ACC-100</AccountNumber>
            <CovFactor>1.00</CovFactor>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
            <ExposureType>Auto</ExposureType>
            <RateEffectiveDate>2023-01-01</RateEffectiveDate>
            <RatingExposureType>Primary</RatingExposureType>
            <Segment>SegmentA</Segment>
            <State>CA</State>
            <Value>1.10</Value>
          </CASSimpleExpsRateTbl_Ext>
        </SimpleExposureRates>
        """,
    )

    result = diff_files(before, after, config)

    assert result.summary["added"] == 0
    assert result.summary["removed"] == 0
    assert result.summary["updated"] == 1
    assert result.updated[0]["key"].startswith("AccountNumber=ACC-200")
