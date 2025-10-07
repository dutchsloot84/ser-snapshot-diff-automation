# Installation & Single-File Binaries

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

## Optional single-file binaries

Environments without Python can rely on PyInstaller or uv to produce standalone executables.

### PyInstaller

```bash
pip install --upgrade pip
pip install pyinstaller
pyinstaller --name ser-diff --onefile --console -p src -m serdiff.cli
```

Artifacts land in `dist/`. Rename per platform if desired (e.g., `ser-diff-linux`, `ser-diff-darwin`). Validate with `./dist/ser-diff --version`.

### uv

[`uv`](https://github.com/astral-sh/uv) can bundle the tool quickly when Python 3.12 is present:

```bash
uv tool install pyinstaller
uv pip install .
pyinstaller --name ser-diff --onefile --console -p src -m serdiff.cli
```

### Windows notes

Run the same command set in PowerShell. The resulting `dist/ser-diff.exe` can be renamed to include the OS suffix. Verify with:

```powershell
./dist/ser-diff.exe doctor
```

## Release automation

GitHub Actions builds and uploads macOS, Linux, and Windows one-file binaries whenever a tagged release is pushed. See [`.github/workflows/release.yml`](../.github/workflows/release.yml) for the reference implementation.
