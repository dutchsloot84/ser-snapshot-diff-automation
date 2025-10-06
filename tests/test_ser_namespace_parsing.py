from __future__ import annotations

from pathlib import Path

from serdiff.diff import diff_files
from serdiff.presets import get_preset

FIXTURES = Path(__file__).parent / "fixtures"


def test_ser_preset_handles_namespaces() -> None:
    config = get_preset("SER").config
    before = FIXTURES / "SER_before_ns.xml"
    after = FIXTURES / "SER_after_ns.xml"

    result = diff_files(before, after, config)

    assert result.summary["total_before"] == 2
    assert result.summary["total_after"] == 2
    assert result.summary["added"] == 1
    assert result.summary["removed"] == 1
    assert result.summary["updated"] == 1
    assert result.meta["namespace_detected"] is True
    assert result.meta["schema"] == "SER"
