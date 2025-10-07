# SER Snapshot Diff Automation (ser-diff)

> Stream, compare, and report PolicyCenter SER/Exposure Types changes with single-file HTML/XLSX artifacts and canonical JSON ready for CI.

**New:** Download the SER Diff GUI, double-click the binary, pick your BEFORE/AFTER XML files, optionally supply a Jira ID, and click **Run Diff**. The generated HTML/XLSX report opens automatically (falling back to the containing folder if needed).

- [GUI Runner](#gui-runner)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Single-file Reports](#single-file-reports)
- [Canonical JSON schema v1.0](#canonical-json-schema-v10)
- [Configuration](#configuration)
- [Guardrails & Exit Codes](#guardrails--exit-codes)
- [Explain & Doctor](#explain--doctor)
- [CI/CD Usage](#cicd-usage)
- [Standard Change SOP](#standard-change-sop)
- [Security Note](#security-note)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Policies & Additional Docs](#policies--additional-docs)
- [Changelog](#changelog)

## GUI Runner

1. Download the latest "SER Diff" GUI zip for your platform from [GitHub Releases](https://github.com/ser-projects/ser-snapshot-diff-automation/releases).
2. Extract the archive and double-click the bundled binary (`SER-Diff.exe`, `SER Diff.app`, or `ser-diff-gui`).
3. Choose BEFORE and AFTER XML exports. The Jira ID field is automatically pre-filled if `.serdiff.toml/.yaml/.json` is present in the working directory.
4. Click **Run Diff**. A timestamped folder beneath `~/SER-Diff-Reports/` is created, the primary report opens directly in your file explorer (with a folder fallback when required), and any guardrail warnings are highlighted in the GUI.
5. Click **Check Environment** any time to run `ser-diff doctor` and confirm local prerequisites.

### Launch options

- `ser-diff-gui` (installed via `pipx install ser-diff` or `pip install .`).
- `python -m serdiff.gui_runner` from a virtual environment.
- One-file binaries built with PyInstaller (`SER-Diff.exe`, `SER Diff.app`, `ser-diff-gui`).

For build instructions and advanced packaging notes, see [docs/install.md](docs/install.md).

## Installation

### pipx (recommended)
- Streaming XML reader powered by `xml.etree.ElementTree.iterparse` for large files.
- Auto Mode detects schemas/namespaces and infers unique keys; inspect results with `ser-diff explain` or the `--explain` flag.
- Presets for SER and Exposure Types tables plus a fully custom mode.
- Field-level diffing with auditable JSON + CSV outputs.
- Threshold and partner guard rails for change management.
- Ready for CI: linting, tests, and demo artifact generation.

```bash
python -m pip install --upgrade pip
pipx install ser-diff
ser-diff doctor
```

### Virtual environment (macOS/Linux)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
ser-diff doctor
```

### Virtual environment (Windows)

```powershell
# PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
ser-diff doctor
```

```bash
# Git Bash / MSYS
python -m venv .venv
source .venv/Scripts/activate
pip install -e .[dev]
ser-diff doctor
```

### Optional one-file binaries

Download-or-build guidance for the CLI and GUI binaries lives in [docs/install.md](docs/install.md). Tagged releases upload macOS/Linux/Windows single-file GUI binaries automatically.

## Quick Start

### Auto Mode (hands-off defaults)

```bash
ser-diff \
  --before exports/Prod_BEFORE_Import_CASSimpleExpsRateTbl_Ext_27198Entries.xml \
  --after  exports/Prod_AFTER_Import_CASSimpleExpsRateTbl_27214Entries.xml \
  --jira MOB-126703 \
  --report html
```

Auto Mode infers the schema (SER vs Exposure Types), composes a unique key, streams XML via `iterparse`, and writes artifacts beneath `reports/<derived-prefix>/`. Add `--output-dir` or `--out-prefix` to override the destination.

### Explicit SER preset

```bash
ser-diff \
  --before exports/Prod_BEFORE_Import_CASSimpleExpsRateTbl_Ext_27198Entries.xml \
  --after  exports/Prod_AFTER_Import_CASSimpleExpsRateTbl_27214Entries.xml \
  --table SER \
  --output-dir reports \
  --out-prefix MOB-126703_Prod_SER_diff \
  --jira MOB-126703 \
  --report xlsx
```

Reports remain available even when guardrails fail. Console summaries flag counts and threshold violations in a single line.

## Single-file Reports

`ser-diff` emits one human artifact per run when `--report` is supplied (CSV exports are skipped). The canonical `diff.json` file always sits beside the chosen report.

- `--report html` generates a self-contained page with sticky headers, filters, partner callouts, diagnostics, and an embedded canonical JSON payload inside `<script type="application/json" id="ser-diff-data">…</script>`.
- `--report xlsx` produces a workbook with `Summary`, `Added`, `Removed`, and `Changed` sheets, frozen header rows, and auto-filters.

Preview tips: open the HTML file locally in a browser or the XLSX workbook in Excel/LibreOffice to capture screenshots when required. Binary assets stay out of version control.

Learn more in [docs/reports.md](docs/reports.md).

## Canonical JSON schema v1.0

Every run writes `diff.json` next to the selected report. The payload is stable (`schema_version = "1.0"`):

```json
{
  "schema_version": "1.0",
  "meta": {
    "generated_at": "2024-06-01T12:34:56Z",
    "tool_version": "1.2.3",
    "table": "SER",
    "key_fields": ["PublicID"],
    "before_file": "exports/Prod_BEFORE...xml",
    "after_file": "exports/Prod_AFTER...xml",
    "jira": "MOB-126703"
  },
  "summary": {
    "added": 2,
    "removed": 0,
    "changed": 1,
    "unexpected_partners": [],
    "thresholds": {
      "max_added": 0,
      "max_removed": 0,
      "violations": ["MAX_ADDED"]
    }
  }
}
```

Programmatic usage:

```bash
# jq: inspect threshold violations
jq '.summary.thresholds' reports/MOB-126703/diff.json
```

```powershell
# PowerShell: list changed keys
get-content reports/MOB-126703/diff.json -Raw |
  ConvertFrom-Json |
  Select-Object -ExpandProperty changed |
  ForEach-Object { $_.key }
```

```python
# Python: export added rows to CSV (when present)
import csv, json
from pathlib import Path
payload = json.loads(Path("reports/MOB-126703/diff.json").read_text())
added = payload["added"]
if added:
    with Path("reports/MOB-126703/added.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=added[0]["record"].keys())
        writer.writeheader()
        for row in added:
            writer.writerow(row["record"])
```

HTML consumers should read the embedded JSON via `JSON.parse(document.getElementById('ser-diff-data').textContent)`.

## Configuration

Configuration files live in the working directory. Priority: `.serdiff.toml` → `.serdiff.yaml` → `.serdiff.json`. CLI flags always win. Generate a starter file with:

```bash
ser-diff init
```

Example TOML:

```toml
[jira]
ticket = "ENG-123"

[io]
output_dir = "reports"
out_prefix = "MOB-126703"

[guards]
expected_partners = ["PartnerOne", "PartnerTwo"]
max_added = 0
max_removed = 0
fail_on_unexpected = true

[preset]
mode = "SER"  # auto | SER | custom

[custom]
# record_path = ".//CustomRecord"
# record_localname = "CustomRecord"
# keys = ["PublicID", "Partner"]
# fields = ["PublicID", "Partner", "State", "Factor"]
# strip_ns = false
```

With config in place the short command works:

```bash
ser-diff --before BEFORE.xml --after AFTER.xml
```

## Guardrails & Exit Codes

- `--max-added` / `--max-removed` cap delta counts.
- `--expected-partners` validates partner coverage.
- `--fail-on-unexpected` flips partner mismatches into hard failures.
- `--strict` upgrades schema/key warnings (e.g., zero rows) to exit code `2`.
- Exit codes: `0` = success, `2` = guardrail violation. Reports are always written.

Console output prints a one-line summary plus explicit warnings when guardrails trip.

## Explain & Doctor

- `ser-diff explain` reveals the detected schema, inferred key fields, namespaces, and diagnostics without writing reports. Add `--json` for machine-readable diagnostics (mirrors the HTML Diagnostics section).
- `ser-diff doctor` prints tool/python versions, OS info, XML parser status, and verifies that `reports/` is writable.

## CI/CD Usage

Integrate `ser-diff` into GitHub Actions or similar pipelines. Example excerpt:

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
    cache: pip
- run: pip install -e .[dev]
- run: make lint test
- run: >-
    ser-diff --before samples/SER_before.xml --after samples/SER_after.xml \
      --table SER --report html --out-prefix demo-ser
- uses: actions/upload-artifact@v4
  with:
    name: ser-diff-reports
    path: reports
```

Guardrail breaches return exit code `2`. Configure CI to treat `2` as failure while still uploading artifacts for review.

Tagged releases can reuse the workflow in [`.github/workflows/release.yml`](.github/workflows/release.yml) to build single-file binaries.

## Standard Change SOP

1. Export BEFORE (SER) from PolicyCenter.
2. Import vendor XML or apply the change.
3. Export AFTER (SER).
4. Run `ser-diff` with Auto Mode or the SER preset and choose `--report html` or `--report xlsx`.
   ```bash
   ser-diff --before BEFORE.xml --after AFTER.xml \
     --table SER --output-dir reports \
     --out-prefix MOBPXD-1213_Prod_SER_diff \
     --jira MOBPXD-1213 --report html
   ```
5. Review the console summary and guardrail status.
6. Attach the generated report and `diff.json` to Jira/change tickets.
7. Proceed only when thresholds and partner checks are green (or documented).

## Security Note

The HTML report embeds canonical JSON safely: `</` sequences are escaped and Unicode line separators (U+2028/U+2029) are guarded to prevent premature script termination. Consumers must parse the payload via `.textContent`.

## Troubleshooting

- **Zero rows**: try `--strip-ns`, widen `--record-path`, or run `ser-diff explain --json` to inspect detection.
- **Duplicate keys**: Auto Mode extends composite keys; review `ser-diff explain` output for candidate fields.
- **Unexpected namespaces**: combine `--strip-ns` with explicit `--record-localname` or configure via `.serdiff.toml`.
- **Windows paths**: quote paths with spaces and prefer PowerShell for better UTF-8 handling; Git Bash works with forward slashes.

## Development

```bash
make fmt    # black + ruff --fix
make lint   # ruff check + black --check
make test   # pytest -q
```

### Build GUI locally

```bash
python -m pip install --upgrade pip
python -m pip install -e .[dev] pyinstaller
```

Then package the Tkinter GUI with PyInstaller:

- **Windows (PowerShell):** `pyinstaller --onefile --windowed -n "SER-Diff" src/serdiff/gui_runner.py`
- **macOS:** `pyinstaller --onefile --windowed -n "SER Diff.app" src/serdiff/gui_runner.py`
- **Linux:** `pyinstaller --onefile --windowed -n "ser-diff-gui" src/serdiff/gui_runner.py`

Artifacts appear under `dist/` ready to zip and share.

### Publish release (GUI binaries)

1. Update `pyproject.toml` and `CHANGELOG.md` with the new version.
2. Commit the changes and push your branch.
3. Tag and push the release:

   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

4. GitHub Actions uploads `SER-Diff-Windows.zip`, `SER-Diff-macOS.zip`, and `SER-Diff-Linux.zip` to the release. Verify the assets and update README links if the repository location changes.

Optional hooks:

```bash
pip install pre-commit
pre-commit install
```

## Policies & Additional Docs

- No committed binary assets (PNG/JPG/XLSX). Generate screenshots locally when required.
- Documentation extras:
  - [docs/install.md](docs/install.md): install & binary build guidance.
  - [docs/reports.md](docs/reports.md): HTML/XLSX features and JSON extraction tips.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release notes covering Auto Mode, configuration loader, single-file reports, canonical JSON v1.0, guardrail behaviour, and documentation updates.
