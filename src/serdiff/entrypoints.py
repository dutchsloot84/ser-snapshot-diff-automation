"""Programmatic entrypoints for GUI and automation integrations."""

from __future__ import annotations

import argparse
import io
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from serdiff.cli import (
    EXIT_GATES_FAILED,
    EXIT_SUCCESS,
    RunSetup,
    _evaluate_thresholds,
    _merge_cli_with_config,
    _parse_expected_partners,
    _resolve_run_setup,
    _run_doctor,
)
from serdiff.config import load_config
from serdiff.diff import diff_files, write_reports


@dataclass(slots=True)
class DiffRunResult:
    """Structured response returned by :func:`run_diff`."""

    exit_code: int
    output_dir: Path
    primary_report: Path | None
    json_path: Path | None
    extra_reports: list[Path] = field(default_factory=list)
    produced: list[Path] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    guardrail_messages: list[str] = field(default_factory=list)
    strict_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _build_default_namespace(
    before: Path,
    after: Path,
    *,
    jira: str | None,
    report: str,
    output_dir: Path | None,
) -> argparse.Namespace:
    """Create an ``argparse.Namespace`` compatible with CLI helpers."""

    namespace = argparse.Namespace(
        before=str(before),
        after=str(after),
        table=None,
        record_path=None,
        record_localname=None,
        strip_ns=None,
        auto=None,
        explain=False,
        strict=False,
        keys=None,
        fields=None,
        out_prefix=None,
        output_dir=str(output_dir) if output_dir else None,
        jira=jira,
        expected_partners=None,
        max_added=None,
        max_removed=None,
        fail_on_unexpected=None,
        format="all",
        report=report,
        excel=None,
    )
    return namespace


def _normalise_arguments(args: argparse.Namespace) -> argparse.Namespace:
    """Apply GUI-friendly defaults after merging with configuration."""

    if args.output_dir is None:
        args.output_dir = "reports"
    if args.out_prefix is None:
        args.out_prefix = "diff_report"
    if args.fail_on_unexpected is None:
        args.fail_on_unexpected = True
    if args.strip_ns is None:
        args.strip_ns = False
    if args.auto is None:
        args.auto = True
    return args


def _gather_strict_issues(result_summary: dict[str, Any], setup: RunSetup) -> list[str]:
    issues: list[str] = []
    if result_summary.get("total_before", 0) == 0:
        issues.append("no BEFORE records parsed")
    if result_summary.get("total_after", 0) == 0:
        issues.append("no AFTER records parsed")
    if setup.warnings:
        issues.extend(setup.warnings)
    return issues


def run_diff(
    *,
    before: str | Path,
    after: str | Path,
    jira: str | None = None,
    report: str = "html",
    output_dir: str | Path | None = None,
) -> DiffRunResult:
    """Execute the diff engine with GUI-safe defaults.

    Parameters
    ----------
    before, after:
        Paths to the BEFORE and AFTER XML files.
    jira:
        Optional Jira identifier to embed in report metadata and filenames.
    report:
        Single-file human readable report format (``"html"`` or ``"xlsx"``).
    output_dir:
        Directory that will receive generated reports. When ``None`` the value is
        resolved via configuration or falls back to ``~/SER-Diff-Reports`` in the GUI
        layer.

    Returns
    -------
    DiffRunResult
        Metadata about the run including exit code and the concrete output paths that
        were generated. ``output_dir`` always points to an existing directory and
        ``primary_report``/``json_path`` resolve to the main artefacts when
        available.
    """

    before_path = Path(before).expanduser().resolve()
    after_path = Path(after).expanduser().resolve()

    if not before_path.is_file():
        raise FileNotFoundError(f"BEFORE XML not found: {before_path}")
    if not after_path.is_file():
        raise FileNotFoundError(f"AFTER XML not found: {after_path}")

    output_path = Path(output_dir).expanduser() if output_dir else None

    loaded_config = load_config(Path.cwd())
    args = _build_default_namespace(
        before=before_path,
        after=after_path,
        jira=jira,
        report=report,
        output_dir=output_path,
    )
    args = _merge_cli_with_config(args, loaded_config)
    args = _normalise_arguments(args)

    setup = _resolve_run_setup(args)
    expected_partners = _parse_expected_partners(args.expected_partners)

    reports_dir = Path(args.output_dir)
    reports_prefix = args.out_prefix
    if args.jira:
        reports_prefix = f"{reports_prefix}_{args.jira}"
    out_prefix = reports_dir / reports_prefix

    result = diff_files(
        before_path,
        after_path,
        setup.config,
        jira=args.jira,
        expected_partners=expected_partners,
        strip_namespaces=bool(args.strip_ns),
    )

    thresholds, threshold_messages = _evaluate_thresholds(
        result,
        expected_partners=expected_partners,
        max_added=args.max_added,
        max_removed=args.max_removed,
    )

    out_prefix.mkdir(parents=True, exist_ok=True)

    produced = write_reports(
        result,
        out_prefix,
        output_format=args.format,
        report_type=args.report,
        thresholds=thresholds,
    )

    produced_paths = [Path(path).expanduser().resolve() for path in produced]

    primary_report: Path | None = None
    json_path: Path | None = None
    extra_reports: list[Path] = []

    for path in produced_paths:
        suffix = path.suffix.lower()
        if path.name == "diff.json":
            json_path = path
            continue
        if suffix in {".html", ".xlsx"} and primary_report is None:
            primary_report = path
            continue
        extra_reports.append(path)

    strict_issues = _gather_strict_issues(result.summary, setup)

    guardrail_triggered = False
    if threshold_messages and args.fail_on_unexpected:
        guardrail_triggered = True
    if args.strict and strict_issues:
        guardrail_triggered = True

    exit_code = EXIT_GATES_FAILED if guardrail_triggered else EXIT_SUCCESS

    return DiffRunResult(
        exit_code=exit_code,
        output_dir=out_prefix.expanduser().resolve(),
        primary_report=primary_report,
        json_path=json_path,
        extra_reports=extra_reports,
        produced=produced_paths,
        summary=dict(result.summary),
        guardrail_messages=list(threshold_messages),
        strict_issues=strict_issues,
        warnings=list(setup.warnings),
    )


def run_doctor() -> tuple[int, str]:
    """Run ``ser-diff doctor`` programmatically and capture its output."""

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
        exit_code = _run_doctor([])
    combined = stdout_buffer.getvalue()
    stderr_text = stderr_buffer.getvalue()
    if stderr_text:
        combined = f"{combined}\n{stderr_text}" if combined else stderr_text
    return exit_code, combined.strip()


__all__ = ["DiffRunResult", "run_diff", "run_doctor"]
