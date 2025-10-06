"""Command line interface for the ser-diff tool."""
from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from . import __version__
from .diff import DiffConfig, diff_files, write_reports
from .presets import get_preset

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_GATES_FAILED = 2


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ser-diff",
        description="Diff BEFORE and AFTER PolicyCenter exports for SER and Exposure Types tables.",
    )
    parser.add_argument("--before", required=True, help="Path to the BEFORE XML export")
    parser.add_argument("--after", required=True, help="Path to the AFTER XML export")

    table_group = parser.add_mutually_exclusive_group(required=False)
    table_group.add_argument("--table", choices=["SER", "EXPOSURE", "custom"], help="Preset table to use")
    table_group.add_argument("--record-path", help="XPath to the repeating record elements")

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
    parser.add_argument("--out-prefix", default="diff_report", help="Output prefix for generated reports")
    parser.add_argument("--jira", help="Jira ID to embed in report metadata and filenames")
    parser.add_argument(
        "--expected-partners",
        help="Comma separated list of expected partners; others will raise alerts",
    )
    parser.add_argument("--max-added", type=int, help="Maximum allowed added records before failing")
    parser.add_argument("--max-removed", type=int, help="Maximum allowed removed records before failing")
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


def _resolve_config(args: argparse.Namespace) -> DiffConfig:
    table_name: str | None = getattr(args, "table", None)

    if args.table and args.table != "custom":
        preset = get_preset(args.table)
        config = preset.config
        fields = list(config.fields)
        record_path = config.record_path
        key_fields = list(config.key_fields)
        table_name = config.table_name
    else:
        if not args.record_path:
            raise SystemExit("--record-path is required when --table is not provided")
        if not args.keys:
            raise SystemExit("At least one --key must be provided for custom tables")
        record_path = args.record_path
        key_fields = [list(args.keys)]
        fields = list(args.keys)

    if args.fields:
        fields = tuple(field.strip() for field in args.fields.split(",") if field.strip())
        if not fields:
            raise SystemExit("--fields must contain at least one field name")
    else:
        fields = tuple(fields)

    key_field_set = {field for key_group in key_fields for field in key_group}
    for key_field in key_field_set:
        if key_field not in fields:
            fields = tuple(list(fields) + [key_field])

    return DiffConfig(
        record_path=record_path,
        fields=fields,
        key_fields=[tuple(group) for group in key_fields],
        table_name=table_name,
    )


def _parse_expected_partners(value: str | None) -> list[str] | None:
    if not value:
        return None
    partners = [partner.strip() for partner in value.split(",") if partner.strip()]
    return partners or None


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)

    config = _resolve_config(args)
    expected_partners = _parse_expected_partners(args.expected_partners)

    before_path = Path(args.before)
    after_path = Path(args.after)

    out_prefix = (
        Path(f"{args.out_prefix}_{args.jira}") if args.jira else Path(args.out_prefix)
    )

    if args.excel:
        print("Excel validation is not implemented yet (TODO)", file=sys.stderr)

    try:
        result = diff_files(
            before_path,
            after_path,
            config,
            jira=args.jira,
            expected_partners=expected_partners,
        )
    except Exception as exc:  # pragma: no cover - CLI guardrail
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    write_reports(result, out_prefix, output_format=args.format)

    exit_code = EXIT_SUCCESS
    failures: list[str] = []

    if expected_partners and result.unexpected_partners:
        failures.append(
            "Unexpected partners detected: " + ", ".join(result.unexpected_partners)
        )

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

    _print_summary(result)
    _print_outputs(result.output_files)

    return exit_code


def _print_summary(result) -> None:
    print("\nDiff Summary")
    print("-------------")
    for key in ["added", "removed", "updated", "total_before", "total_after", "total_changed"]:
        if key in result.summary:
            print(f"{key.replace('_', ' ').title()}: {result.summary[key]}")
    if result.unexpected_partners:
        print("Unexpected partners: " + ", ".join(result.unexpected_partners))


def _print_outputs(paths: Iterable[str]) -> None:
    print("\nGenerated reports:")
    for path in paths:
        print(f"  - {path}")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
