"""Command line interface for the ser-diff tool."""

from __future__ import annotations

import argparse
import os
import platform
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from . import __version__
from .detect import ROW_INDEX_FIELD, detect_schema, infer_fields, infer_key_fields, probe_xml
from .diff import DiffConfig, diff_files, write_reports
from .presets import get_preset

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_GATES_FAILED = 2


@dataclass
class RunSetup:
    config: DiffConfig
    auto_mode: bool
    explain: dict[str, object]
    warnings: list[str]


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ser-diff",
        description="Diff BEFORE and AFTER PolicyCenter exports for SER and Exposure Types tables.",
    )
    parser.add_argument("--before", required=True, help="Path to the BEFORE XML export")
    parser.add_argument("--after", required=True, help="Path to the AFTER XML export")

    table_group = parser.add_mutually_exclusive_group(required=False)
    table_group.add_argument(
        "--table", choices=["SER", "EXPOSURE", "custom"], help="Preset table to use"
    )
    table_group.add_argument("--record-path", help="XPath to the repeating record elements")

    parser.add_argument(
        "--record-localname",
        help="Localname of the record element (ignores XML namespaces)",
    )
    parser.add_argument(
        "--strip-ns",
        action="store_true",
        help="Strip XML namespaces during parsing (useful for default namespaces)",
    )

    parser.add_argument(
        "--auto",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Automatically detect schema, keys, and fields (default when no table provided)",
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help="Print detected schema, key, and field information",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 2 when zero rows or warnings are encountered",
    )

    parser.add_argument(
        "--key",
        action="append",
        dest="keys",
        help="Field to use as part of the composite key (repeatable)",
    )
    parser.add_argument(
        "--fields",
        help="Comma separated list of fields to compare (overrides preset)",
    )
    parser.add_argument(
        "--out-prefix", default="diff_report", help="Output prefix for generated reports"
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory to store generated reports (created if missing)",
    )
    parser.add_argument("--jira", help="Jira ID to embed in report metadata and filenames")
    parser.add_argument(
        "--expected-partners",
        help="Comma separated list of expected partners; others will raise alerts",
    )
    parser.add_argument(
        "--max-added", type=int, help="Maximum allowed added records before failing"
    )
    parser.add_argument(
        "--max-removed", type=int, help="Maximum allowed removed records before failing"
    )
    parser.add_argument(
        "--fail-on-unexpected",
        action="store_true",
        help="Exit with status 2 if unexpected partners or thresholds are exceeded",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv", "all"],
        default="all",
        help="Report format to generate",
    )
    parser.add_argument(
        "--excel",
        help="Optional Excel workbook for future validation (stub)",
    )
    parser.add_argument("--version", action="version", version=f"ser-diff {__version__}")

    return parser.parse_args(argv)


def _parse_doctor_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ser-diff doctor",
        description="Validate the local environment for running ser-diff.",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("reports"),
        help="Directory ser-diff uses for report output (default: ./reports)",
    )
    return parser.parse_args(argv)


def _check_reports_dir(path: Path) -> tuple[bool, str]:
    raw = path.expanduser()
    try:
        target = raw.resolve()
    except FileNotFoundError:  # pragma: no cover - resolve may fail on some platforms
        target = (Path.cwd() / raw).resolve()

    if target.exists() and not target.is_dir():
        return False, f"{target} exists but is not a directory"

    check_path = target if target.exists() else target.parent
    if not str(check_path):
        check_path = Path.cwd()

    existing_parent = check_path
    while not existing_parent.exists() and existing_parent != existing_parent.parent:
        existing_parent = existing_parent.parent

    writable = os.access(existing_parent, os.W_OK | os.X_OK)

    if target.exists():
        description = f"{target} (writable)" if writable else f"{target} (not writable)"
        return writable, description

    description = f"{target} (will be created)"
    if not writable:
        description = f"{target} (cannot create directory)"
    return writable, description


def _check_xml_parser() -> tuple[bool, str]:
    try:
        from xml.etree.ElementTree import iterparse
    except Exception as exc:  # pragma: no cover - defensive guard
        return False, f"xml.etree.ElementTree import failed: {exc}"

    if not callable(iterparse):
        return False, "xml.etree.ElementTree.iterparse unavailable"
    return True, "xml.etree.ElementTree.iterparse available"


def _run_doctor(argv: Sequence[str] | None = None) -> int:
    args = _parse_doctor_args(argv)
    checks: list[tuple[str, bool, str]] = []

    checks.append(("ser-diff version", True, __version__))
    checks.append(("Python version", True, platform.python_version()))
    checks.append(("Operating system", True, platform.platform()))

    reports_ok, reports_detail = _check_reports_dir(args.reports_dir)
    checks.append(("Reports directory", reports_ok, reports_detail))

    xml_ok, xml_detail = _check_xml_parser()
    checks.append(("XML parser", xml_ok, xml_detail))

    all_ok = all(status for _, status, _ in checks)

    for label, passed, detail in checks:
        status = "OK" if passed else "FAIL"
        print(f"[{status}] {label}: {detail}")

    if all_ok:
        print("\nDoctor summary: All systems go.")
        return EXIT_SUCCESS

    print("\nDoctor summary: Issues detected. Please address the failed checks above.")
    return EXIT_FAILURE


def _ensure_fields_include_keys(
    fields: Sequence[str], candidates: Sequence[Sequence[str]]
) -> list[str]:
    ordered: list[str] = list(fields)
    for candidate in candidates:
        for field_name in candidate:
            if field_name == ROW_INDEX_FIELD:
                continue
            if field_name not in ordered:
                ordered.append(field_name)
    return ordered


def _configure_auto(args: argparse.Namespace) -> tuple[DiffConfig, dict[str, object], list[str]]:
    before_path = Path(args.before)
    after_path = Path(args.after)

    before_probe = probe_xml(before_path)
    after_probe = probe_xml(after_path)

    schema_before = detect_schema(before_probe)
    schema_after = detect_schema(after_probe) if after_probe.records else schema_before

    schema_info = schema_before
    if schema_info.name == "UNKNOWN" and schema_after.name != "UNKNOWN":
        schema_info = schema_after

    combined_records = list(before_probe.records)
    if after_probe.records:
        combined_records.extend(after_probe.records)

    if not combined_records:
        combined_records = list(before_probe.records or after_probe.records)

    key_candidates: list[list[str]] = []
    seen_candidates: set[tuple[str, ...]] = set()
    for candidate in infer_key_fields(combined_records):
        candidate_tuple = tuple(candidate)
        if candidate_tuple and candidate_tuple not in seen_candidates:
            seen_candidates.add(candidate_tuple)
            key_candidates.append(list(candidate))
    for candidate in schema_info.key_candidates:
        candidate_tuple = tuple(candidate)
        if candidate_tuple and candidate_tuple not in seen_candidates:
            seen_candidates.add(candidate_tuple)
            key_candidates.append(list(candidate))

    if not key_candidates:
        key_candidates = [[ROW_INDEX_FIELD]]

    primary_key = tuple(key_candidates[0]) if key_candidates[0] else (ROW_INDEX_FIELD,)
    fallback = tuple(tuple(candidate) for candidate in key_candidates[1:])

    inferred_fields = infer_fields(combined_records, schema_info)
    if not inferred_fields:
        inferred_fields = [field for field in primary_key if field != ROW_INDEX_FIELD]
    inferred_fields = _ensure_fields_include_keys(inferred_fields, key_candidates)

    record_localname = schema_info.record_localname or args.record_localname

    config = DiffConfig(
        record_path=".//*",
        fields=tuple(inferred_fields),
        key_fields=primary_key,
        composite_fallback=fallback,
        table_name=schema_info.name if schema_info.name not in {"", "UNKNOWN"} else None,
        record_localname=record_localname,
        schema=schema_info.name,
    )

    explain = {
        "mode": "auto",
        "schema_detected": schema_info.name,
        "record_localname": record_localname,
        "fields": inferred_fields,
        "key_candidates": key_candidates,
        "namespaces_seen": before_probe.namespace_detected or after_probe.namespace_detected,
    }

    warnings: list[str] = []
    if schema_before.name != schema_after.name and schema_after.name != "UNKNOWN":
        warnings.append(
            "Schema mismatch detected between BEFORE and AFTER exports; proceeding with "
            f"{schema_info.name}"
        )
        explain["schema_mismatch"] = {
            "before": schema_before.name,
            "after": schema_after.name,
        }

    return config, explain, warnings


def _configure_manual(args: argparse.Namespace) -> tuple[DiffConfig, dict[str, object]]:
    explain: dict[str, object] = {}

    if args.table and args.table != "custom":
        preset = get_preset(args.table)
        base_config = preset.config
        record_path = base_config.record_path
        key_fields = tuple(base_config.key_fields)
        composite_fallback = tuple(tuple(group) for group in base_config.composite_fallback)
        fields = list(base_config.fields)
        record_localname = base_config.record_localname
        table_name = base_config.table_name
        schema = base_config.schema
        explain.update({"mode": "preset", "table": preset.name})
    else:
        if not args.record_path:
            raise SystemExit("--record-path is required when --table is not provided")
        if not args.keys:
            raise SystemExit("At least one --key must be provided for custom tables")
        record_path = args.record_path
        key_fields = tuple(args.keys)
        composite_fallback = (tuple(list(key_fields) + [ROW_INDEX_FIELD]),)
        fields = (
            [field.strip() for field in args.fields.split(",") if field.strip()]
            if args.fields
            else list(key_fields)
        )
        record_localname = args.record_localname
        table_name = None
        schema = "CUSTOM"
        explain.update({"mode": "custom", "record_path": record_path})

    if args.fields and args.table and args.table != "custom":
        fields = [field.strip() for field in args.fields.split(",") if field.strip()]

    if not fields:
        fields = [field for field in key_fields if field and field != ROW_INDEX_FIELD]

    candidates = [key_fields] + [tuple(group) for group in composite_fallback]
    fields = _ensure_fields_include_keys(fields, candidates)

    record_localname = args.record_localname or record_localname

    config = DiffConfig(
        record_path=record_path,
        fields=tuple(fields),
        key_fields=key_fields if key_fields else (ROW_INDEX_FIELD,),
        composite_fallback=composite_fallback,
        table_name=table_name,
        record_localname=record_localname,
        schema=schema,
    )

    explain.update(
        {
            "record_localname": record_localname,
            "fields": fields,
            "key_candidates": [list(candidate) for candidate in candidates],
        }
    )

    return config, explain


def _resolve_run_setup(args: argparse.Namespace) -> RunSetup:
    auto_mode = args.auto if args.auto is not None else not args.table and not args.record_path

    if auto_mode and args.keys:
        auto_mode = False

    if auto_mode:
        config, explain, warnings = _configure_auto(args)
    else:
        config, explain = _configure_manual(args)
        warnings = []

    if args.fields and auto_mode:
        override_fields = [field.strip() for field in args.fields.split(",") if field.strip()]
        if not override_fields:
            raise SystemExit("--fields must contain at least one field name")
        override_fields = _ensure_fields_include_keys(
            override_fields, [config.key_fields, *config.composite_fallback]
        )
        config.fields = tuple(override_fields)
        explain["fields"] = override_fields

    if args.record_localname:
        config.record_localname = args.record_localname
        explain["record_localname"] = args.record_localname

    return RunSetup(config=config, auto_mode=auto_mode, explain=explain, warnings=warnings)


def _parse_expected_partners(value: str | None) -> list[str] | None:
    if not value:
        return None
    partners = [partner.strip() for partner in value.split(",") if partner.strip()]
    return partners or None


def main(argv: Sequence[str] | None = None) -> int:
    argv_list = list(sys.argv[1:]) if argv is None else list(argv)

    if argv_list and argv_list[0] == "doctor":
        return _run_doctor(argv_list[1:])

    args = _parse_args(argv_list)

    setup = _resolve_run_setup(args)
    config = setup.config
    expected_partners = _parse_expected_partners(args.expected_partners)

    before_path = Path(args.before)
    after_path = Path(args.after)

    reports_dir = Path(args.output_dir)
    reports_prefix = args.out_prefix
    if args.jira:
        reports_prefix = f"{reports_prefix}_{args.jira}"
    out_prefix = reports_dir / reports_prefix

    if args.excel:
        print("Excel validation is not implemented yet (TODO)", file=sys.stderr)

    for warning in setup.warnings:
        print(f"Warning: {warning}", file=sys.stderr)

    try:
        result = diff_files(
            before_path,
            after_path,
            config,
            jira=args.jira,
            expected_partners=expected_partners,
            strip_namespaces=args.strip_ns,
        )
    except Exception as exc:  # pragma: no cover - CLI guardrail
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    produced_paths = write_reports(result, out_prefix, output_format=args.format)

    strict_issues: list[str] = []

    if result.summary.get("total_before", 0) == 0:
        _print_zero_row_hint("BEFORE", config.record_localname)
        strict_issues.append("no BEFORE records parsed")
    if result.summary.get("total_after", 0) == 0:
        _print_zero_row_hint("AFTER", config.record_localname)
        strict_issues.append("no AFTER records parsed")

    if setup.warnings:
        strict_issues.extend(setup.warnings)

    exit_code = EXIT_SUCCESS
    failures: list[str] = []

    if expected_partners and result.unexpected_partners:
        failures.append("Unexpected partners detected: " + ", ".join(result.unexpected_partners))

    added = result.summary.get("added", 0)
    removed = result.summary.get("removed", 0)

    if args.max_added is not None and added > args.max_added:
        failures.append(f"Added records {added} exceed threshold {args.max_added}")
    if args.max_removed is not None and removed > args.max_removed:
        failures.append(f"Removed records {removed} exceed threshold {args.max_removed}")

    if failures:
        message = "; ".join(failures)
        print(f"\nGATES FAILED: {message}", file=sys.stderr)
        exit_code = EXIT_GATES_FAILED if args.fail_on_unexpected else EXIT_FAILURE

    summary = result.summary
    summary_line = (
        f"Diff: added={summary.get('added', 0)} removed={summary.get('removed', 0)} "
        f"updated={summary.get('updated', 0)} "
        f"(before={summary.get('total_before', 0)}, after={summary.get('total_after', 0)}). "
        f"Reports at: {out_prefix}"
    )
    print(summary_line)

    duplicates_meta = result.meta.get("duplicates_resolved", {})
    key_fields_used = result.meta.get("key_fields_used", [])
    if duplicates_meta.get("resolved"):
        detail = duplicates_meta.get("details")
        key_display = ", ".join(key_fields_used)
        if detail:
            print(
                f"Note: composite key auto-extended to ensure uniqueness ({detail}). "
                f"Final key: {key_display}"
            )
        else:
            print(
                f"Note: composite key auto-extended to ensure uniqueness. Final key: {key_display}"
            )

    print("Generated reports:")
    for path in produced_paths:
        print(f"  - {path}")

    if args.explain:
        _print_explain(setup, result)

    if args.strict and strict_issues:
        exit_code = max(exit_code, EXIT_GATES_FAILED)

    return exit_code


def _print_explain(setup: RunSetup, result) -> None:
    meta = result.meta
    print("\nExplain")
    print("-------")
    mode = "auto" if setup.auto_mode else setup.explain.get("mode", "manual")
    print(f"Mode: {mode}")
    print(f"Schema: {meta.get('schema', 'UNKNOWN')}")
    print(f"Record localname: {meta.get('record_localname') or 'n/a'}")
    fields_used = ", ".join(meta.get("fields_used", []))
    print(f"Fields used: {fields_used or 'n/a'}")
    key_used = ", ".join(meta.get("key_fields_used", []))
    print(f"Key fields: {key_used or 'n/a'}")
    duplicates = meta.get("duplicates_resolved", {})
    if duplicates.get("resolved"):
        detail = duplicates.get("details") or "fallback key applied"
        print(f"Duplicate handling: {detail}")
    else:
        print("Duplicate handling: primary key unique")
    print(f"Namespaces detected: {'yes' if meta.get('namespace_detected') else 'no'}")
    key_candidates = setup.explain.get("key_candidates")
    if key_candidates:
        printable = [", ".join(candidate) for candidate in key_candidates]
        print("Key candidates tried: " + "; ".join(printable))
    if setup.warnings:
        print("Warnings:")
        for warning in setup.warnings:
            print(f"  - {warning}")


def _print_zero_row_hint(which: str, record_localname: str | None) -> None:
    expected_localname = record_localname or "CASSimpleExpsRateTbl_Ext"
    print(
        f"\nNo records parsed from {which}. Tips:\n"
        f" • XML namespaces can hide elements (try --strip-ns or --record-localname {expected_localname})\n"
        " • Record element may differ (for SER use --table SER, expecting CASSimpleExpsRateTbl_Ext)\n"
        " • Relax the record filter (e.g. --record-path .//* with --record-localname)",
        file=sys.stderr,
    )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
