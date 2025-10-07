# Single-File Reports

`ser-diff` produces one human-facing artifact per run when `--report` is supplied. CSV exports are skipped in favour of a single HTML page or XLSX workbook and the canonical `diff.json` is written alongside the artifact.

## HTML report

- Self-contained document with inline CSS/JS (no external dependencies).
- Sections: Header, Summary (counts + thresholds), Added, Removed, Changed tables, Diagnostics, and embedded canonical JSON.
- Sticky table headers, column filters, and partner badges improve review speed.
- JSON is embedded as `<script type="application/json" id="ser-diff-data">…</script>` with `</` and Unicode line separators escaped to prevent premature termination.

Extract the payload from the page:

```bash
python - <<'PY'
from pathlib import Path
import json
from bs4 import BeautifulSoup
html = Path('reports/demo-ser/demo-ser.html').read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'html.parser')
payload = json.loads(soup.find('script', id='ser-diff-data').text)
print(payload['summary'])
PY
```

If BeautifulSoup is unavailable, parse via the DOM in a browser:

```javascript
const payload = JSON.parse(document.getElementById('ser-diff-data').textContent);
console.log(payload.summary);
```

## XLSX report

- Workbook contains `Summary`, `Added`, `Removed`, and `Changed` worksheets.
- Headers are frozen and auto-filter is enabled for each sheet.
- The Summary sheet highlights guardrail thresholds and partner mismatches.

Example verification with `openpyxl`:

```python
from io import BytesIO
from openpyxl import load_workbook
wb = load_workbook('reports/demo-ser/demo-ser.xlsx', data_only=True)
print(wb.sheetnames)
summary = wb['Summary']
print([cell.value for cell in next(summary.iter_rows(min_row=1, max_row=1))])
```

## Canonical JSON companion

Both report types write `diff.json` alongside the artifact. The JSON follows schema v1.0 and mirrors the Summary counts displayed in the UI.

## Screenshots

We avoid storing binary screenshots in git. To capture a preview, open the generated HTML/XLSX locally and capture your own image before sharing in tickets or documentation.
