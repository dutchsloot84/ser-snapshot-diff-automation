# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Tkinter GUI runner (`serdiff.gui_runner`) that wraps the existing diff engine, remembers the last directory, integrates `ser-diff doctor`, and auto-opens the generated reports folder.
- Programmatic entrypoints (`serdiff.entrypoints`) for running diffs and doctor checks from the GUI and future automation.
- PyInstaller spec (`pyinstaller/ser-diff-gui.spec`) plus release automation to build one-file GUI binaries for Windows, macOS, and Linux with zipped artifacts per platform.
- GUI smoke tests covering helper utilities and a headless launch path.
- `ser-diff doctor` command that validates Python, OS, XML parser support, and report directory permissions.
- pipx-first installation guidance and installation doctor documentation.
- Release automation to build and upload single-file binaries on tagged releases.
- `docs/install.md` with PyInstaller build steps for macOS, Linux, and Windows.
- Repo-local configuration loader with `.serdiff.toml` precedence (TOML > YAML > JSON) and a `ser-diff init` generator.
- CLI now honours config defaults while keeping CLI flags authoritative and supports `--no-fail-on-unexpected`/`--no-strip-ns` overrides.
- Canonical `diff.json` (schema v1.0) emitted for every run including threshold metadata for CI automation.
- Single-file HTML reporting via `--report html` with inline assets and an embedded canonical JSON payload.
- Single-file XLSX reporting via `--report xlsx` that mirrors the HTML report with Summary/Added/Removed/Changed worksheets.
- `ser-diff explain` subcommand (with `--json`) for reusable diagnostics plus richer console summaries during `ser-diff` runs.
- Guardrail handling now exits with status `2` when `--fail-on-unexpected` or `--strict` flags are set while still producing all report artifacts.
- Example CI release workflow (`.github/workflows/release.yml`) and README guidance covering artifact uploads and tagged binary builds.
- `ser-diff-gui` console entry point for launching the GUI after installation.

### Fixed
- Safely escape embedded JSON in the HTML report to prevent premature `</script>` termination and retain Unicode line separators.
- GUI now opens the generated primary report (or its folder) reliably and `DiffRunResult` exposes concrete report paths for automation consumers.
- GUI imports now use absolute `serdiff.` paths so PyInstaller one-file builds run without package-context errors.
- ci(release): fix macOS script path; add preflight guard; set fail-fast=false.

### Docs
- README quick-start for the GUI runner and refreshed installation notes covering download/build steps for one-file binaries.
- Refreshed README-first documentation with installation paths, quick-start guides, single-file report coverage, canonical JSON usage, guardrails, SOP, and troubleshooting guidance aligned to the current CLI.
- Updated `docs/install.md` for pipx/venv workflows and binary build steps, and introduced `docs/reports.md` covering HTML/XLSX features and JSON extraction tips.
- Added README and `docs/install.md` sections describing local GUI builds and the release tagging workflow for binary distribution.
- Documented the stable GUI script path, Gatekeeper guidance, and CI build safeguards (preflight + independent matrix) for the PyInstaller workflow.
