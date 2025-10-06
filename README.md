# SER Snapshot Diff Automation

`ser-diff` is a lightweight, production-ready CLI for diffing PolicyCenter system-table XML exports. It specialises in Simple Exposure Rates (SER) and Exposure Types tables, producing JSON/CSV artifacts that can be attached directly to Jira and change tickets.

## Features

- Streaming XML reader powered by `xml.etree.ElementTree.iterparse` for large files.
- Auto Mode detects schemas/namespaces and infers unique keys with optional `--explain` output.
- Presets for SER and Exposure Types tables plus a fully custom mode.
- Field-level diffing with auditable JSON + CSV outputs.
- Threshold and partner guard rails for change management.
- Ready for CI: linting, tests, and demo artifact generation.

## Installation

Use `pipx` for isolated installs, or fall back to a virtual environment:

```bash
pipx install ser-diff
# or from a checkout
pipx install .

python -m pip install --upgrade pip setuptools wheel
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### Windows virtual environment

```powershell
# PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]

# Git Bash / MINGW64
python -m venv .venv
source .venv/Scripts/activate
pip install -e .[dev]
```

## Quick Start

### Check your environment

```bash
ser-diff doctor
```

The doctor command prints version information, verifies XML parsing support, and ensures the default `reports/` directory is writable.

### Auto Mode (recommended)

```bash
ser-diff \
  --before exports/Prod_BEFORE_Import_CASSimpleExpsRateTbl_Ext.xml \
  --after  exports/Prod_AFTER_Import_CASSimpleExpsRateTbl_Ext.xml \
  --jira MOB-126703
```

Auto Mode is enabled automatically whenever you omit `--table`/`--record-path`. Reports are written to `reports/` by default; use `--output-dir` to pick a different location. Add `--auto` explicitly if you prefer to be explicit.

### What Auto Mode does

- Detects PolicyCenter schemas (SER vs Exposure Types) by probing element local names.
- Handles default or prefixed namespaces without additional flags; `--strip-ns` is available for tricky files.
- Infers a stable key: `PublicID` when unique, otherwise a composite that is extended with additional fields (and, if required, a row counter) to avoid duplicate-key crashes.
- Prints a one-line summary plus friendly zero-row diagnostics; `--explain` reveals the detected schema, fields, key candidates, and namespace status.

### PolicyCenter SER (explicit preset)

```bash
ser-diff \
  --before exports/Prod_BEFORE_Import_CASSimpleExpsRateTbl_Ext_27198Entries.xml \
  --after  exports/Prod_AFTER_Import_CASSimpleExpsRateTbl_27214Entries.xml \
  --table SER \
  --output-dir reports \
  --out-prefix MOB-126703_Prod_SER_diff \
  --jira MOB-126703

# Still seeing 0 rows? Try widening the filters:
ser-diff \
  --before exports/Prod_BEFORE_Import_CASSimpleExpsRateTbl_Ext_27198Entries.xml \
  --after  exports/Prod_AFTER_Import_CASSimpleExpsRateTbl_27214Entries.xml \
  --record-path .//* \
  --record-localname CASSimpleExpsRateTbl_Ext \
  --key AccountNumber --key CovFactor --key EffectiveDate --key ExpirationDate \
  --key RateEffectiveDate --key RatingExposureType --key Segment --key State \
  --fields AccountNumber,CovFactor,EffectiveDate,ExpirationDate,ExposureType,RateEffectiveDate,RatingExposureType,Segment,State,Value \
  --output-dir reports \
  --out-prefix MOB-126703_Prod_SER_diff \
  --jira MOB-126703 \
  --strip-ns
```

### Custom tables

```bash
ser-diff \
  --before before.xml \
  --after after.xml \
  --record-path .//CustomRecord \
  --key PublicID --key Partner \
  --fields PublicID,Partner,State,Factor \
  --output-dir reports \
  --out-prefix custom_diff
```

## SOP Snippet (Standard Change)

1. Export BEFORE (SER) from PolicyCenter.
2. Import the Jira-provided XML (e.g. `MOBPXD-1213_SerImport.xml`).
3. Export AFTER (SER).
4. Run the diff:
   ```bash
   ser-diff --before BEFORE.xml --after AFTER.xml --table SER \
     --out-prefix reports/MOBPXD-1213_Prod_SER_diff --jira MOBPXD-1213
   ```
5. Review the console summary.
6. Attach the generated JSON/CSV files to Jira and the Change ticket.
7. Proceed only if summary counts and thresholds are green.

## Thresholds and Partners

- `--max-added` / `--max-removed` enforce safety rails. Set `--fail-on-unexpected` to exit with status `2` if the gates are breached (reports are still written).
- `--expected-partners` validates the `Partner` column. Unexpected partners are highlighted and can fail the run with `--fail-on-unexpected`.
- `--strict` upgrades warnings (zero rows, schema mismatches) to exit status `2` so CI can block on unexpected inputs.

## Performance Notes

The XML reader uses `iterparse` to stream records and clear elements once processed. This keeps memory usage flat even for multi-gigabyte exports. Keys are validated for duplicates, and composite keys are supported for SER when `PublicID` is missing.

## Demo Data

Sample SER and Exposure XML files live in `samples/`. Run `make demo` to generate reference reports in `reports/`.

## Development

```bash
make venv      # create a virtual environment with dev deps
make fmt       # run black + ruff --fix
make lint      # run ruff linting
make test      # run pytest
make demo      # build sample reports
```

CI runs linting, tests, and demo generation on Python 3.10 and 3.12. Reports are uploaded as artifacts for traceability.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release notes.

## License

MIT License. See [LICENSE](LICENSE).
