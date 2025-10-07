# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
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

### Fixed
- Safely escape embedded JSON in the HTML report to prevent premature `</script>` termination and retain Unicode line separators.
