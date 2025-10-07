# Installation & Single-File Binaries

## SER Diff GUI (one-file binaries)

### Download and run

1. Grab the latest platform zip from the [Releases page](https://github.com/ser-projects/ser-snapshot-diff-automation/releases).
2. Extract the archive and double-click the binary (`SER-Diff.exe`, `SER-Diff.app`, or `ser-diff-gui`).
3. Select BEFORE and AFTER XML files, confirm the optional Jira ticket, and click **Run Diff**. The generated HTML/XLSX report opens automatically (with a folder fallback if the OS cannot launch the file directly).
4. Use **Check Environment** to run `ser-diff doctor` if you encounter issues.

> **macOS Gatekeeper:** On first launch, right-click `SER-Diff.app`, choose **Open**, and confirm the prompt if macOS warns about an unidentified developer.

### Build GUI locally with PyInstaller

Prerequisites: Python 3.10+, `pip install -e .[dev] pyinstaller`, and platform SDKs (Xcode command line tools on macOS, Visual Studio Build Tools on Windows) when required by PyInstaller.

Install build dependencies once:

```bash
python -m pip install --upgrade pip
python -m pip install -e .[dev] pyinstaller
```

Build commands (use the same sources we ship from CI):

#### Windows (PowerShell)

```powershell
pyinstaller --onefile --windowed -n "SER-Diff" src/serdiff/gui_runner.py
```

#### macOS (Terminal)

```bash
pyinstaller --onefile --windowed -n "SER-Diff" src/serdiff/gui_runner.py
```

#### Linux (Terminal)

```bash
pyinstaller --onefile --windowed -n "ser-diff-gui" src/serdiff/gui_runner.py
```

PyInstaller places the finished binaries under `dist/`. Zip each platform output for distribution (the GitHub Release workflow names the archives `SER-Diff-Windows.zip`, `SER-Diff-macOS.zip`, and `SER-Diff-Linux.zip`). The CI job invokes PyInstaller directly with `src/serdiff/gui_runner.py`, so keep that path stable—if the script moves, update the workflow and rerun the preflight check locally before tagging.

## pipx (recommended)

```bash
python -m pip install --upgrade pip
pipx install ser-diff
ser-diff doctor
```

## Virtual environments

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
ser-diff doctor
```

### Windows

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

## Publish Release (GUI binaries)

1. Update `pyproject.toml` with the new version and add a matching entry in `CHANGELOG.md`.
2. Commit the changes and push your branch.
3. Tag the release and push the tag:

   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

4. GitHub Actions builds and uploads the Windows, macOS, and Linux GUI zips (`SER-Diff-Windows.zip`, `SER-Diff-macOS.zip`, `SER-Diff-Linux.zip`) to the release. Each matrix job sets `fail-fast: false`, so other platforms continue even if one build fails.
5. Validate the assets on the Releases page and update documentation links if the organization or repository name changes.

### Troubleshooting

- *ImportError: attempted relative import with no known parent package* → rebuild after ensuring all GUI imports use the `serdiff.` prefix (absolute imports).
- *Windows SmartScreen warning* → select **More info → Run anyway** until code signing is available.
- *ERROR: src/serdiff/gui_runner.py not found* during CI → verify the script exists at that path and re-run the workflow; the preflight step intentionally fails fast while the matrix keeps running for other OS targets.

Release automation details live in [`.github/workflows/release.yml`](../.github/workflows/release.yml).
