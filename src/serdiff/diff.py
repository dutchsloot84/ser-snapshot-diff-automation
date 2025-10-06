"""Core diff logic for SER Snapshot Diff Automation."""

from __future__ import annotations

import csv
import hashlib
import json
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .detect import ROW_INDEX_FIELD


def _local_name(tag: str | None) -> str:
    if not tag:
        return ""
    if "}" in tag:
        tag = tag.split("}", 1)[1]
    if ":" in tag:
        tag = tag.split(":", 1)[1]
    return tag


def _normalise_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.strip().split())


@dataclass
class DiffConfig:
    record_path: str
    fields: Sequence[str]
    key_fields: Sequence[str]
    table_name: str | None = None
    record_localname: str | None = None
    composite_fallback: Sequence[Sequence[str]] = ()
    schema: str = "UNKNOWN"

    def __post_init__(self) -> None:
        if not self.fields:
            raise ValueError("fields must not be empty")
        if not self.key_fields:
            raise ValueError("key_fields must not be empty")

    def candidate_keys(self) -> list[list[str]]:
        candidates: list[list[str]] = [list(self.key_fields)]
        for fallback in self.composite_fallback:
            candidates.append(list(fallback))
        if not candidates:
            candidates.append([ROW_INDEX_FIELD])
        return candidates


@dataclass
class DiffResult:
    summary: dict[str, int]
    meta: dict[str, object]
    added: list[dict[str, object]]
    removed: list[dict[str, object]]
    updated: list[dict[str, object]]
    unexpected_partners: list[str] = field(default_factory=list)
    output_files: list[str] = field(default_factory=list)


class DuplicateKeyError(RuntimeError):
    """Raised when duplicate keys are encountered within the same dataset."""


def _ensure_field_coverage(
    fields: Sequence[str], key_candidates: Sequence[Sequence[str]]
) -> list[str]:
    ordered: list[str] = list(fields)
    for candidate in key_candidates:
        for field_name in candidate:
            if field_name == ROW_INDEX_FIELD:
                continue
            if field_name not in ordered:
                ordered.append(field_name)
    return ordered


def _parse_records(
    xml_path: Path,
    record_localname: str | None,
    fields: Sequence[str],
    *,
    strip_ns: bool = False,
) -> tuple[list[dict[str, str]], bool]:
    records: list[dict[str, str]] = []
    namespace_detected = False

    events = ("start", "end") if strip_ns else ("end",)
    context = ET.iterparse(str(xml_path), events=events)

    for event, elem in context:
        if strip_ns and event == "start":
            if "}" in elem.tag or ":" in elem.tag:
                namespace_detected = True
            elem.tag = _local_name(elem.tag)
            continue

        if event != "end":
            continue

        if "}" in elem.tag or ":" in elem.tag:
            namespace_detected = True

        if record_localname and _local_name(elem.tag) != record_localname:
            continue

        values: dict[str, str] = {}
        for child in elem:
            if "}" in child.tag or ":" in child.tag:
                namespace_detected = True
            child_name = _local_name(child.tag)
            if child_name not in values:
                values[child_name] = _normalise_text(child.text)

        if not values:
            elem.clear()
            continue

        record = {field_name: values.get(field_name, "") for field_name in fields}
        records.append(record)
        elem.clear()

    return records, namespace_detected


def _compute_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collect_partners(records: Iterable[dict[str, str]]) -> list[str]:
    partners: list[str] = []
    for record in records:
        partner = record.get("Partner", "")
        if partner:
            partners.append(partner)
    return partners


def _make_key(
    record: dict[str, str],
    key_fields: Sequence[str],
    counters: dict[tuple[tuple[str, str], ...], int],
) -> str:
    base_components = tuple(
        (field, record.get(field, "")) for field in key_fields if field != ROW_INDEX_FIELD
    )
    row_value = ""
    if ROW_INDEX_FIELD in key_fields:
        count = counters.get(base_components, 0) + 1
        counters[base_components] = count
        row_value = str(count)

    parts: list[str] = []
    for key_field in key_fields:
        if key_field == ROW_INDEX_FIELD:
            parts.append(f"{ROW_INDEX_FIELD}={row_value}")
        else:
            parts.append(f"{key_field}={record.get(key_field, '')}")
    return "|".join(parts)


def _has_duplicates(records: Sequence[dict[str, str]], key_fields: Sequence[str]) -> bool:
    seen: set[str] = set()
    counters: dict[tuple[tuple[str, str], ...], int] = {}
    for record in records:
        key = _make_key(record, key_fields, counters)
        if key in seen:
            return True
        seen.add(key)
    return False


def _describe_key_transition(
    candidate: Sequence[str], primary_candidate: Sequence[str], index: int
) -> str:
    if index == 0:
        return ""

    primary_set = set(primary_candidate)
    new_fields = [field for field in candidate if field not in primary_set]
    if not new_fields:
        return "used fallback key"

    if new_fields == [ROW_INDEX_FIELD]:
        return "appended row index for uniqueness"

    if ROW_INDEX_FIELD in new_fields:
        extras = [field for field in new_fields if field != ROW_INDEX_FIELD]
        if extras:
            return f"added {', '.join(extras)} and row index to key"
        return "appended row index for uniqueness"

    return "added " + ", ".join(new_fields) + " to key"


def _select_candidate(
    datasets: Sequence[Sequence[dict[str, str]]],
    candidates: Sequence[Sequence[str]],
) -> tuple[list[str], dict[str, object]]:
    if not candidates:
        candidates = ([ROW_INDEX_FIELD],)

    primary = candidates[0]
    for index, candidate in enumerate(candidates):
        if all(not _has_duplicates(records, candidate) for records in datasets):
            has_values = any(
                any(
                    record.get(field_name, "")
                    for field_name in candidate
                    if field_name != ROW_INDEX_FIELD
                )
                for records in datasets
                for record in records
            )
            if not has_values:
                continue
            details = _describe_key_transition(candidate, primary, index)
            info: dict[str, object] = {
                "resolved": index > 0,
                "details": details or None,
            }
            return list(candidate), info

    fallback = list(primary)
    if ROW_INDEX_FIELD not in fallback:
        fallback.append(ROW_INDEX_FIELD)
    info = {
        "resolved": True,
        "details": _describe_key_transition(fallback, primary, len(candidates))
        or "appended row index for uniqueness",
    }
    return fallback, info


def _build_record_map(
    records: Sequence[dict[str, str]],
    key_fields: Sequence[str],
) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    counters: dict[tuple[tuple[str, str], ...], int] = {}
    for record in records:
        key = _make_key(record, key_fields, counters)
        mapping[key] = record
    return mapping


def diff_files(
    before: Path,
    after: Path,
    config: DiffConfig,
    *,
    jira: str | None = None,
    expected_partners: Sequence[str] | None = None,
    record_localname: str | None = None,
    strip_namespaces: bool = False,
) -> DiffResult:
    effective_localname = record_localname or config.record_localname
    key_candidates = config.candidate_keys()
    effective_fields = _ensure_field_coverage(config.fields, key_candidates)

    before_records_raw, before_ns = _parse_records(
        before, effective_localname, effective_fields, strip_ns=strip_namespaces
    )
    after_records_raw, after_ns = _parse_records(
        after, effective_localname, effective_fields, strip_ns=strip_namespaces
    )

    key_fields_used, duplicates_info = _select_candidate(
        [before_records_raw, after_records_raw], key_candidates
    )

    before_records = _build_record_map(before_records_raw, key_fields_used)
    after_records = _build_record_map(after_records_raw, key_fields_used)

    added: list[dict[str, object]] = []
    removed: list[dict[str, object]] = []
    updated: list[dict[str, object]] = []

    for key, after_record in sorted(after_records.items()):
        if key not in before_records:
            added.append(
                {
                    "key": key,
                    "key_fields": list(key_fields_used),
                    "before": {},
                    "after": after_record,
                }
            )

    for key, before_record in sorted(before_records.items()):
        if key not in after_records:
            removed.append(
                {
                    "key": key,
                    "key_fields": list(key_fields_used),
                    "before": before_record,
                    "after": {},
                }
            )

    for key in sorted(set(before_records) & set(after_records)):
        before_record = before_records[key]
        after_record = after_records[key]
        changes = {}
        for field_name in effective_fields:
            before_value = before_record.get(field_name, "")
            after_value = after_record.get(field_name, "")
            if before_value != after_value:
                changes[field_name] = {"before": before_value, "after": after_value}
        if changes:
            updated.append(
                {
                    "key": key,
                    "key_fields": list(key_fields_used),
                    "changes": changes,
                    "before": before_record,
                    "after": after_record,
                }
            )

    partner_pool = _collect_partners(after_records.values()) + _collect_partners(
        before_records.values()
    )
    unique_partners = sorted(set(partner_pool))
    unexpected_partners: list[str] = []
    if expected_partners:
        expected_set = {partner.strip() for partner in expected_partners if partner.strip()}
        unexpected_partners = sorted(
            {partner for partner in unique_partners if partner not in expected_set}
        )

    summary = {
        "added": len(added),
        "removed": len(removed),
        "updated": len(updated),
        "total_before": len(before_records),
        "total_after": len(after_records),
        "total_changed": len(added) + len(removed) + len(updated),
    }

    namespace_detected = before_ns or after_ns

    meta = {
        "jira": jira,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "table": config.table_name,
        "schema": config.schema,
        "record_path": config.record_path,
        "record_localname": effective_localname,
        "fields_used": list(effective_fields),
        "key_fields_used": list(key_fields_used),
        "duplicates_resolved": duplicates_info,
        "namespace_detected": namespace_detected,
        "partners_detected": unique_partners,
        "expected_partners": list(expected_partners) if expected_partners else [],
        "input_files": [
            {"role": "before", "path": str(before), "sha256": _compute_hash(before)},
            {"role": "after", "path": str(after), "sha256": _compute_hash(after)},
        ],
        "before_file": str(before),
        "after_file": str(after),
        "tool_version": __version__,
    }

    return DiffResult(
        summary=summary,
        meta=meta,
        added=added,
        removed=removed,
        updated=updated,
        unexpected_partners=unexpected_partners,
    )


def _build_canonical_payload(
    result: DiffResult, thresholds: dict[str, object] | None = None
) -> dict[str, object]:
    thresholds = thresholds or {}
    summary = result.summary
    meta = result.meta

    table_value = meta.get("table") or meta.get("schema") or "CUSTOM"
    if isinstance(table_value, str) and table_value.upper() == "UNKNOWN":
        table_value = "CUSTOM"

    key_fields = meta.get("key_fields_used") or []
    if not isinstance(key_fields, list):
        key_fields = list(key_fields)

    before_file = meta.get("before_file")
    after_file = meta.get("after_file")
    if not before_file or not after_file:
        for entry in meta.get("input_files", []):
            if entry.get("role") == "before" and not before_file:
                before_file = entry.get("path")
            if entry.get("role") == "after" and not after_file:
                after_file = entry.get("path")

    def _build_changes(record: dict[str, object]) -> dict[str, dict[str, str]]:
        delta: dict[str, dict[str, str]] = {}
        for field_name, change in record.get("changes", {}).items():
            before_value = change.get("before", "")
            after_value = change.get("after", "")
            delta[field_name] = {"from": before_value, "to": after_value}
        return delta

    payload_meta: dict[str, object] = {
        "generated_at": meta.get("generated_at"),
        "tool_version": meta.get("tool_version", __version__),
        "table": table_value,
        "key_fields": key_fields,
        "before_file": before_file,
        "after_file": after_file,
        "jira": meta.get("jira"),
    }

    if meta.get("schema"):
        payload_meta["schema"] = meta.get("schema")
    if meta.get("duplicates_resolved") is not None:
        payload_meta["duplicates_resolved"] = meta.get("duplicates_resolved")
    if meta.get("namespace_detected") is not None:
        payload_meta["namespace_detected"] = meta.get("namespace_detected")
    if meta.get("fields_used"):
        payload_meta["fields_used"] = meta.get("fields_used")
    if meta.get("key_fields_used"):
        payload_meta["key_fields_used"] = meta.get("key_fields_used")

    payload = {
        "schema_version": "1.0",
        "meta": payload_meta,
        "summary": {
            "added": summary.get("added", 0),
            "removed": summary.get("removed", 0),
            "changed": summary.get("updated", 0),
            "total_before": summary.get("total_before", 0),
            "total_after": summary.get("total_after", 0),
            "unexpected_partners": list(result.unexpected_partners),
            "thresholds": {
                "max_added": thresholds.get("max_added"),
                "max_removed": thresholds.get("max_removed"),
                "violations": list(thresholds.get("violations", [])),
            },
        },
        "added": [
            {"key": record.get("key"), "record": record.get("after", {})}
            for record in result.added
        ],
        "removed": [
            {"key": record.get("key"), "record": record.get("before", {})}
            for record in result.removed
        ],
        "changed": [
            {
                "key": record.get("key"),
                "before": record.get("before", {}),
                "after": record.get("after", {}),
                "delta": _build_changes(record),
            }
            for record in result.updated
        ],
    }

    return payload


def write_reports(
    result: DiffResult,
    out_prefix: Path,
    *,
    output_format: str = "all",
    thresholds: dict[str, object] | None = None,
) -> list[str]:
    out_prefix.mkdir(parents=True, exist_ok=True)
    produced: list[str] = []

    json_path = out_prefix / "diff.json"
    payload = _build_canonical_payload(result, thresholds)
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    produced.append(str(json_path))

    if output_format in {"all", "csv"}:
        csv_prefix = out_prefix / out_prefix.name
        produced.extend(_write_csv_reports(result, csv_prefix))

    result.output_files = produced
    return produced


def _write_csv_reports(result: DiffResult, out_prefix: Path) -> list[str]:
    produced: list[str] = []

    summary_path = Path(f"{out_prefix}_summary.csv")
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        for metric, value in result.summary.items():
            writer.writerow([metric, value])
        writer.writerow(["unexpected_partners", ";".join(result.unexpected_partners)])
    produced.append(str(summary_path))

    added_path = Path(f"{out_prefix}_added.csv")
    _write_record_csv(added_path, result.added)
    produced.append(str(added_path))

    removed_path = Path(f"{out_prefix}_removed.csv")
    _write_record_csv(removed_path, result.removed)
    produced.append(str(removed_path))

    updated_path = Path(f"{out_prefix}_updated.csv")
    with updated_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["key", "field", "before", "after"])
        for record in result.updated:
            key = record.get("key", "")
            changes = record.get("changes", {})
            for field, change in changes.items():
                writer.writerow([key, field, change.get("before", ""), change.get("after", "")])
    produced.append(str(updated_path))

    return produced


def _write_record_csv(path: Path, records: Sequence[dict[str, object]]) -> None:
    base_headers = sorted(
        {
            *(key for record in records for key in record),
            "key",
        }
    )
    headers = [header for header in base_headers if header not in {"before", "after", "changes"}]
    headers += ["before", "after"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for record in records:
            row = []
            for header in headers:
                if header == "before" or header == "after":
                    value = record.get(header, {})
                    row.append(json.dumps(value, ensure_ascii=False, sort_keys=True))
                else:
                    value = record.get(header, "")
                    if isinstance(value, list | dict):
                        row.append(json.dumps(value, ensure_ascii=False, sort_keys=True))
                    else:
                        row.append(value)
            writer.writerow(row)


__all__ = [
    "DiffConfig",
    "DiffResult",
    "DuplicateKeyError",
    "diff_files",
    "write_reports",
]
