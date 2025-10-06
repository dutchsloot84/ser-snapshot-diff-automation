import json
from pathlib import Path

from serdiff import __version__, cli
from serdiff.diff import diff_files, write_reports
from serdiff.presets import get_preset


def write_xml(path: Path, body: str) -> Path:
    path.write_text(body.strip(), encoding="utf-8")
    return path


def test_canonical_json_schema_and_delta(tmp_path: Path) -> None:
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
          <ExposureType>
            <PublicID>EXP-002</PublicID>
            <ExposureCode>AUTO</ExposureCode>
            <Partner>Lyft</Partner>
            <State>CA</State>
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
            <State>CA</State>
            <EffectiveDate>2023-01-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
          </ExposureType>
          <ExposureType>
            <PublicID>EXP-003</PublicID>
            <ExposureCode>AUTO</ExposureCode>
            <Partner>DoorDash</Partner>
            <State>TX</State>
            <EffectiveDate>2023-06-01</EffectiveDate>
            <ExpirationDate>2023-12-31</ExpirationDate>
          </ExposureType>
        </ExposureTypes>
        """,
    )

    preset = get_preset("EXPOSURE")
    result = diff_files(
        before,
        after,
        preset.config,
        jira="MOB-123",
        expected_partners=["Uber"],
    )

    thresholds, _ = cli._evaluate_thresholds(
        result,
        expected_partners=["Uber"],
        max_added=0,
        max_removed=0,
    )

    out_dir = tmp_path / "reports" / "run"
    produced = write_reports(result, out_dir, output_format="json", thresholds=thresholds)

    json_path = out_dir / "diff.json"
    assert str(json_path) in produced

    with json_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["schema_version"] == "1.0"

    meta = payload["meta"]
    assert meta["tool_version"] == __version__
    assert meta["table"] == "EXPOSURE"
    assert meta["jira"] == "MOB-123"
    assert meta["before_file"].endswith("before.xml")
    assert meta["after_file"].endswith("after.xml")
    assert meta["key_fields"] == ["PublicID"]
    assert "generated_at" in meta and meta["generated_at"]

    summary = payload["summary"]
    assert summary["added"] == 1
    assert summary["removed"] == 1
    assert summary["changed"] == 1
    assert set(summary["unexpected_partners"]) == {"Lyft", "DoorDash"}

    thresholds_summary = summary["thresholds"]
    assert thresholds_summary["max_added"] == 0
    assert thresholds_summary["max_removed"] == 0
    assert {"MAX_ADDED", "MAX_REMOVED", "UNEXPECTED_PARTNER"}.issubset(
        set(thresholds_summary["violations"])
    )

    added_records = payload["added"]
    assert added_records[0]["record"]["PublicID"] == "EXP-003"

    removed_records = payload["removed"]
    assert removed_records[0]["record"]["PublicID"] == "EXP-002"

    changed_records = payload["changed"]
    assert changed_records[0]["delta"]["State"] == {"from": "NY", "to": "CA"}
    assert changed_records[0]["before"]["State"] == "NY"
    assert changed_records[0]["after"]["State"] == "CA"
