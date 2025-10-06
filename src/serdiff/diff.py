"""Core diff logic for SER Snapshot Diff Automation."""

from __future__ import annotations

import csv
import hashlib
import json
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def _strip_namespace(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _normalise_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.strip().split())


@dataclass
class DiffConfig:
    record_path: str
    fields: Sequence[str]
    key_fields: Sequence[Sequence[str]]
    table_name: str | None = None

    def __post_init__(self) -> None:
        if not self.fields:
            raise ValueError("fields must not be empty")
        if not self.key_fields:
            raise ValueError("key_fields must not be empty")


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


def _iter_records(
    xml_path: Path,
    record_path: str,
    fields: Sequence[str],
    key_sets: Sequence[Sequence[str]],
) -> Iterator[tuple[str, Sequence[str], dict[str, str]]]:
    """Yield records extracted from the XML file.

    Yields tuples of (key_string, key_fields_used, record_dict).
    """

    if record_path.endswith("//"):
        raise ValueError("record_path must not end with //")

    path_parts = [part for part in record_path.split("/") if part and part != "."]
    if not path_parts:
        raise ValueError(f"Invalid record_path: {record_path}")

    target_tag = path_parts[-1]

    def matches_path(elem: ET.Element) -> bool:
        return _strip_namespace(elem.tag) == target_tag

    context = ET.iterparse(str(xml_path), events=("end",))
    for _event, elem in context:
        if not matches_path(elem):
            continue

        record: dict[str, str] = {}
        for field_name in fields:
            record[field_name] = _normalise_text(_find_child_text(elem, field_name))

        key_string, key_fields_used = _derive_key(record, key_sets)
        yield key_string, key_fields_used, record
        elem.clear()


def _find_child_text(elem: ET.Element, child_name: str) -> str | None:
    target = child_name.lower()
    for child in elem:
        if _strip_namespace(child.tag).lower() == target:
            return child.text
    return None


def _derive_key(
    record: dict[str, str], key_sets: Sequence[Sequence[str]]
) -> tuple[str, Sequence[str]]:
    for key_fields in key_sets:
        values = [record.get(field, "") for field in key_fields]
        if any(value for value in values):
            key_string = "|".join(
                f"{field}={value}" for field, value in zip(key_fields, values, strict=True)
            )
            return key_string, key_fields
    raise ValueError("Unable to derive key for record; all key fields are empty")


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


def diff_files(
    before: Path,
    after: Path,
    config: DiffConfig,
    *,
    jira: str | None = None,
    expected_partners: Sequence[str] | None = None,
) -> DiffResult:
    before_records: dict[str, dict[str, str]] = {}
    before_keys_used: dict[str, Sequence[str]] = {}
    for key, key_fields_used, record in _iter_records(
        before, config.record_path, config.fields, config.key_fields
    ):
        if key in before_records:
            raise DuplicateKeyError(f"Duplicate key {key!r} found in BEFORE file {before}")
        before_records[key] = record
        before_keys_used[key] = key_fields_used

    after_records: dict[str, dict[str, str]] = {}
    after_keys_used: dict[str, Sequence[str]] = {}
    for key, key_fields_used, record in _iter_records(
        after, config.record_path, config.fields, config.key_fields
    ):
        if key in after_records:
            raise DuplicateKeyError(f"Duplicate key {key!r} found in AFTER file {after}")
        after_records[key] = record
        after_keys_used[key] = key_fields_used

    added: list[dict[str, object]] = []
    removed: list[dict[str, object]] = []
    updated: list[dict[str, object]] = []

    for key, after_record in sorted(after_records.items()):
        if key not in before_records:
            added.append(
                {
                    "key": key,
                    "key_fields": list(after_keys_used[key]),
                    "before": {},
                    "after": after_record,
                }
            )

    for key, before_record in sorted(before_records.items()):
        if key not in after_records:
            removed.append(
                {
                    "key": key,
                    "key_fields": list(before_keys_used[key]),
                    "before": before_record,
                    "after": {},
                }
            )

    for key in sorted(set(before_records) & set(after_records)):
        before_record = before_records[key]
        after_record = after_records[key]
        changes = {}
        for field_name in config.fields:
            before_value = before_record.get(field_name, "")
            after_value = after_record.get(field_name, "")
            if before_value != after_value:
                changes[field_name] = {"before": before_value, "after": after_value}
        if changes:
            updated.append(
                {
                    "key": key,
                    "key_fields": list(before_keys_used.get(key, ())),
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

    meta = {
        "jira": jira,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "table": config.table_name,
        "before_file": {
            "path": str(before),
            "sha256": _compute_hash(before),
        },
        "after_file": {
            "path": str(after),
            "sha256": _compute_hash(after),
        },
        "record_path": config.record_path,
        "fields": list(config.fields),
        "key_fields": [list(keys) for keys in config.key_fields],
        "partners_detected": unique_partners,
        "expected_partners": list(expected_partners) if expected_partners else [],
    }

    return DiffResult(
        summary=summary,
        meta=meta,
        added=added,
        removed=removed,
        updated=updated,
        unexpected_partners=unexpected_partners,
    )


def write_reports(result: DiffResult, out_prefix: Path, *, output_format: str = "all") -> list[str]:
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    produced: list[str] = []

    if output_format in {"all", "json"}:
        json_path = out_prefix.with_suffix(".json")
        payload = {
            "summary": result.summary,
            "meta": result.meta,
            "added": result.added,
            "removed": result.removed,
            "updated": result.updated,
            "unexpected_partners": result.unexpected_partners,
        }
        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        produced.append(str(json_path))

    if output_format in {"all", "csv"}:
        produced.extend(_write_csv_reports(result, out_prefix))

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
