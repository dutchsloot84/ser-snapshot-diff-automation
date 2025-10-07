import json
import re
from pathlib import Path

from serdiff import cli
from serdiff.diff import diff_files, write_reports
from serdiff.presets import get_preset


def write_xml(path: Path, body: str) -> Path:
    path.write_text(body.strip(), encoding="utf-8")
    return path


def extract_embedded_json(html_text: str) -> dict[str, object]:
    match = re.search(
        r"<script type=\"application/json\" id=\"ser-diff-data\">(.*?)</script>",
        html_text,
        re.DOTALL,
    )
    assert match, "Embedded JSON script tag not found"
    return json.loads(match.group(1))


def test_html_report_contains_canonical_payload(tmp_path: Path) -> None:
    before = write_xml(
        tmp_path / "before.xml",
        """
        <ExposureTypes>
          <ExposureType>
            <PublicID>EXP-001</PublicID>
            <ExposureCode>AUTO</ExposureCode>
            <Partner>Uber</Partner>
            <State>NY</State>
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
            <Partner>Lyft</Partner>
            <State>CA</State>
          </ExposureType>
          <ExposureType>
            <PublicID>EXP-002</PublicID>
            <ExposureCode>AUTO</ExposureCode>
            <Partner>DoorDash</Partner>
            <State>TX</State>
          </ExposureType>
        </ExposureTypes>
        """,
    )

    preset = get_preset("EXPOSURE")
    result = diff_files(
        before,
        after,
        preset.config,
        jira="MOB-555",
        expected_partners=["Uber"],
    )

    thresholds, _ = cli._evaluate_thresholds(
        result,
        expected_partners=["Uber"],
        max_added=0,
        max_removed=0,
    )

    out_dir = tmp_path / "reports" / "run"
    produced = write_reports(
        result,
        out_dir,
        output_format="json",
        report_type="html",
        thresholds=thresholds,
    )

    json_path = out_dir / "diff.json"
    html_path = out_dir / f"{out_dir.name}.html"

    assert str(json_path) in produced
    assert str(html_path) in produced

    with json_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    html_text = html_path.read_text(encoding="utf-8")
    embedded_payload = extract_embedded_json(html_text)

    assert embedded_payload == payload

    summary = payload["summary"]
    assert (
        f"<span class=\"summary-label\">Added</span><span class=\"badge\">{summary['added']}</span>"
        in html_text
    )
    assert (
        f"<span class=\"summary-label\">Removed</span><span class=\"badge\">{summary['removed']}</span>"
        in html_text
    )
    assert (
        f"<span class=\"summary-label\">Changed</span><span class=\"badge\">{summary['changed']}"
        in html_text
    )
