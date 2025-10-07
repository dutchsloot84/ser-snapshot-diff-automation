import json
import re

from serdiff.diff import DiffResult
from serdiff.report_html import render_html_report


def _build_result(value: str) -> tuple[DiffResult, dict[str, object], dict[str, object]]:
    result = DiffResult(
        summary={"added": 0, "removed": 0, "updated": 1},
        meta={
            "table": "TEST",
            "schema": "TEST",
            "generated_at": "2024-01-01T00:00:00Z",
            "tool_version": "1.0.0",
            "before_file": "before.xml",
            "after_file": "after.xml",
            "key_fields_used": ["PublicID"],
            "fields_used": ["Value"],
            "record_path": "/ExposureTypes/ExposureType",
            "record_localname": "ExposureType",
            "jira": "MOB-1",
        },
        added=[],
        removed=[],
        updated=[
            {
                "key": "EXP-1",
                "before": {"Value": value},
                "after": {"Value": "ok"},
                "changes": {"Value": {"before": value, "after": "ok"}},
            }
        ],
        unexpected_partners=[],
    )

    payload = {
        "schema_version": "1.0",
        "meta": {
            "generated_at": "2024-01-01T00:00:00Z",
            "tool_version": "1.0.0",
            "table": "TEST",
            "key_fields": ["PublicID"],
            "before_file": "before.xml",
            "after_file": "after.xml",
            "jira": "MOB-1",
        },
        "summary": {
            "added": 0,
            "removed": 0,
            "changed": 1,
            "unexpected_partners": [],
            "thresholds": {
                "max_added": None,
                "max_removed": None,
                "violations": [],
            },
        },
        "added": [],
        "removed": [],
        "changed": [
            {
                "key": "EXP-1",
                "before": {"Value": value},
                "after": {"Value": "ok"},
                "delta": {"Value": {"from": value, "to": "ok"}},
            }
        ],
    }

    thresholds = {"violations": []}
    return result, payload, thresholds


def _extract_payload_text(html: str) -> str:
    match = re.search(
        r"<script type=\"application/json\" id=\"ser-diff-data\">(.*?)</script>",
        html,
        re.DOTALL,
    )
    assert match, "Embedded JSON script tag not found"
    return match.group(1)


def test_json_injected_safely_with_script_ender() -> None:
    marker = "</script><div id='pwned'>"
    result, payload, thresholds = _build_result(marker)
    html = render_html_report(result, payload, thresholds)
    script_text = _extract_payload_text(html)

    assert "</script>" not in script_text

    round_tripped = json.loads(script_text)
    assert round_tripped["changed"][0]["before"]["Value"].startswith("</script")


def test_json_injected_safely_with_line_separators() -> None:
    value = "Line1\u2028Line2\u2029End"
    result, payload, thresholds = _build_result(value)
    html = render_html_report(result, payload, thresholds)
    script_text = _extract_payload_text(html)

    round_tripped = json.loads(script_text)
    assert round_tripped["changed"][0]["before"]["Value"] == value
