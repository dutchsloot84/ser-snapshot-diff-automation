# Installation & Single-File Binaries

## SER Diff GUI (one-file binaries)

### Download and run

1. Grab the latest platform zip from the [Releases page](https://github.com/ser-projects/ser-snapshot-diff-automation/releases).
2. Extract the archive and double-click the binary (`SER-Diff.exe`, `SER Diff.app`, or `ser-diff-gui`).
3. Select BEFORE and AFTER XML files, confirm the optional Jira ticket, and click **Run Diff**. The reports folder opens automatically.
4. Use **Check Environment** to run `ser-diff doctor` if you encounter issues.

### Build locally with PyInstaller

All commands assume Python 3.12 is available. The spec reads the desired binary name from `SERDIFF_GUI_NAME` to account for platform-specific naming.

```bash
python -m pip install --upgrade pip
python -m pip install .[dev] pyinstaller
```

#### Windows (PowerShell)

```powershell
$env:SERDIFF_GUI_NAME = "SER-Diff"
pyinstaller --clean pyinstaller/ser-diff-gui.spec
```

#### macOS (Terminal)

```bash
SERDIFF_GUI_NAME="SER Diff" pyinstaller --clean pyinstaller/ser-diff-gui.spec
```

#### Linux (Terminal)

```bash
SERDIFF_GUI_NAME="ser-diff-gui" pyinstaller --clean pyinstaller/ser-diff-gui.spec
```

PyInstaller writes the binary to `dist/<name>/`. Package the executable (and the generated `README_RUN_ME.txt` from CI) into a zip when distributing manually.

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

## Release automation

GitHub Actions builds and uploads macOS, Linux, and Windows SER Diff GUI one-file binaries whenever a tagged release is pushed. See [`.github/workflows/release.yml`](../.github/workflows/release.yml) for the reference implementation.
