"""Heuristics to detect PolicyCenter export schemas and key fields."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

SER_RECORD_LOCALNAME = "CASSimpleExpsRateTbl_Ext"
SER_FIELD_HINTS = {
    "AccountNumber",
    "CovFactor",
    "ExposureType",
    "RateEffectiveDate",
    "RatingExposureType",
    "Segment",
    "State",
    "EffectiveDate",
    "ExpirationDate",
    "Value",
}

EXPOSURE_RECORD_LOCALNAME = "ExposureType"
ROW_INDEX_FIELD = "__row_index__"


@dataclass
class ProbeRecord:
    """A lightweight record captured during probing."""

    localname: str
    fields: dict[str, str]


@dataclass
class ProbeResult:
    """Collection of sampled records and namespace metadata."""

    records: list[ProbeRecord]
    namespace_detected: bool


@dataclass
class SchemaInfo:
    """Information about a detected schema."""

    name: str
    record_localname: str
    default_fields: list[str]
    key_candidates: list[list[str]]


def _local_name(tag: str | None) -> str:
    if not tag:
        return ""
    if "}" in tag:
        tag = tag.split("}", 1)[1]
    if ":" in tag:
        tag = tag.split(":", 1)[1]
    return tag


def _normalise(text: str | None) -> str:
    if text is None:
        return ""
    return " ".join(text.strip().split())


def probe_xml(xml_path: Path | str, sample_size: int = 2000) -> ProbeResult:
    """Sample an XML file to gather record localnames and field hints."""

    records: list[ProbeRecord] = []
    namespace_detected = False
    path = Path(xml_path)

    for _, elem in ET.iterparse(path, events=("end",)):
        if "}" in elem.tag or ":" in elem.tag:
            namespace_detected = True
        localname = _local_name(elem.tag)
        if not list(elem):
            elem.clear()
            continue

        values: dict[str, str] = {}
        for child in elem:
            if "}" in child.tag or ":" in child.tag:
                namespace_detected = True
            child_name = _local_name(child.tag)
            if child_name not in values:
                values[child_name] = _normalise(child.text)

        if values:
            records.append(ProbeRecord(localname=localname, fields=values))
        elem.clear()
        if len(records) >= sample_size:
            break

    return ProbeResult(records=records, namespace_detected=namespace_detected)


def detect_schema(probe: ProbeResult) -> SchemaInfo:
    """Return the best schema match for the provided probe."""

    records = probe.records
    if not records:
        return SchemaInfo(
            name="UNKNOWN",
            record_localname="",
            default_fields=[],
            key_candidates=[[ROW_INDEX_FIELD]],
        )

    counts = Counter(record.localname for record in records)
    field_index: dict[str, set[str]] = {}
    for record in records:
        field_index.setdefault(record.localname, set()).update(record.fields.keys())

    def _ser_schema(localname: str) -> SchemaInfo:
        return SchemaInfo(
            name="SER",
            record_localname=localname,
            default_fields=[
                "AccountNumber",
                "CovFactor",
                "ExposureType",
                "RateEffectiveDate",
                "RatingExposureType",
                "Segment",
                "State",
                "EffectiveDate",
                "ExpirationDate",
                "Value",
            ],
            key_candidates=[
                ["PublicID"],
                [
                    "AccountNumber",
                    "CovFactor",
                    "ExposureType",
                    "RatingExposureType",
                    "Segment",
                    "State",
                    "EffectiveDate",
                    "RateEffectiveDate",
                    "ExpirationDate",
                ],
                [
                    "AccountNumber",
                    "CovFactor",
                    "ExposureType",
                    "RatingExposureType",
                    "Segment",
                    "State",
                    "EffectiveDate",
                    "RateEffectiveDate",
                    "ExpirationDate",
                    "Value",
                ],
                [
                    "AccountNumber",
                    "CovFactor",
                    "ExposureType",
                    "RatingExposureType",
                    "Segment",
                    "State",
                    "EffectiveDate",
                    "RateEffectiveDate",
                    "ExpirationDate",
                    "Value",
                    ROW_INDEX_FIELD,
                ],
            ],
        )

    for localname, available_fields in field_index.items():
        if localname == SER_RECORD_LOCALNAME:
            return _ser_schema(localname)
        if SER_FIELD_HINTS.issubset(available_fields):
            return _ser_schema(localname)

    if EXPOSURE_RECORD_LOCALNAME in field_index:
        return SchemaInfo(
            name="EXPOSURE",
            record_localname=EXPOSURE_RECORD_LOCALNAME,
            default_fields=[
                "PublicID",
                "ExposureCode",
                "Partner",
                "State",
                "EffectiveDate",
                "ExpirationDate",
            ],
            key_candidates=[["PublicID"], ["PublicID", ROW_INDEX_FIELD]],
        )

    most_common_localname, _ = counts.most_common(1)[0]
    detected_fields = sorted(field_index.get(most_common_localname, set()))
    key_candidates: list[list[str]] = []
    if detected_fields:
        key_candidates.append([detected_fields[0]])
    key_candidates.append([ROW_INDEX_FIELD])
    return SchemaInfo(
        name="UNKNOWN",
        record_localname=most_common_localname,
        default_fields=detected_fields,
        key_candidates=key_candidates,
    )


def infer_key_fields(records: Iterable[ProbeRecord]) -> list[list[str]]:
    """Return candidate key field combinations ordered by preference."""

    records = list(records)
    if not records:
        return [[ROW_INDEX_FIELD]]

    def is_unique(field: str) -> bool:
        values = [record.fields.get(field, "") for record in records]
        if not all(values):
            return False
        return len(set(values)) == len(values)

    candidates: list[list[str]] = []

    if is_unique("PublicID"):
        candidates.append(["PublicID"])

    composite = [
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
    candidates.append(composite)
    candidates.append(composite + ["Value"])
    candidates.append(composite + ["Value", ROW_INDEX_FIELD])
    return candidates


def infer_fields(records: Iterable[ProbeRecord], schema: SchemaInfo | None = None) -> list[str]:
    """Return a stable field ordering for the dataset."""

    if schema and schema.default_fields:
        fields = list(schema.default_fields)
    else:
        union: set[str] = set()
        for record in records:
            union.update(record.fields.keys())
        fields = sorted(union)
    return fields


__all__ = [
    "ProbeRecord",
    "ProbeResult",
    "SchemaInfo",
    "ROW_INDEX_FIELD",
    "probe_xml",
    "detect_schema",
    "infer_key_fields",
    "infer_fields",
]
