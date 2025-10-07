# Installation and Single-File Binaries

`ser-diff` is published as a standard Python package. The recommended way to install it is with [`pipx`](https://pipx.pypa.io/):

```bash
pipx install ser-diff
```

When developing locally, you can also install from a checkout:

```bash
pipx install .
```

## Building Single-File Binaries

For environments that do not have Python available, you can produce self-contained executables using [PyInstaller](https://pyinstaller.org/en/stable/). The commands below assume you are running them from the project root.

### macOS and Linux

```bash
pipx run pyinstaller --name ser-diff --onefile --console -p src -m serdiff.cli
mkdir -p dist
mv dist/ser-diff dist/ser-diff-$(uname -s | tr '[:upper:]' '[:lower:]')
```

The resulting binary is placed in `dist/ser-diff-linux` on Linux and `dist/ser-diff-darwin` on macOS. Copy it to your desired distribution channel.

### Windows (PowerShell)

```powershell
pipx run pyinstaller --name ser-diff --onefile --console -p src -m serdiff.cli
Rename-Item dist\ser-diff.exe dist\ser-diff-windows.exe
```

After building, run the executable with `ser-diff.exe doctor` to confirm it works on the target machine.

## Release Automation

Tagged releases automatically build the three single-file binaries (Windows, macOS, Linux) and upload them as GitHub release assets. See `.github/workflows/ci.yml` for details.
