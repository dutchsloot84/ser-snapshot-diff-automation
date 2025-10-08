"""HTML report rendering for ser-diff."""

from __future__ import annotations

import html
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from serdiff.diff import DiffResult


def safe_json_for_script(payload: dict[str, object]) -> str:
    """Serialise JSON for embedding inside a ``<script type="application/json">`` tag."""

    serialised = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    serialised = serialised.replace("</", "<\\/")
    serialised = serialised.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return serialised


def _escape(value: object) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def _collect_columns(result: DiffResult) -> list[str]:
    meta = result.meta
    ordered: list[str] = []

    for field in meta.get("key_fields_used", []) or []:
        if field and field not in ordered:
            ordered.append(field)

    for field in meta.get("fields_used", []) or []:
        if field and field not in ordered:
            ordered.append(field)

    sources = []
    sources.extend(entry.get("after", {}) for entry in result.added)
    sources.extend(entry.get("before", {}) for entry in result.removed)
    for entry in result.updated:
        sources.append(entry.get("before", {}))
        sources.append(entry.get("after", {}))

    for record in sources:
        if not isinstance(record, dict):
            continue
        for field in record:
            if field and field not in ordered:
                ordered.append(field)

    return ordered


def _render_table_header(columns: list[str]) -> str:
    headers = ['<th scope="col">Key</th>']
    headers.extend(f'<th scope="col">{_escape(column)}</th>' for column in columns)
    return "".join(headers)


def _render_record_row(entry: dict[str, object], columns: list[str], *, record_key: str) -> str:
    key_cell = f"<td class=\"cell-key\">{_escape(entry.get('key'))}</td>"
    record = entry.get(record_key, {})
    values: list[str] = []
    if isinstance(record, dict):
        for column in columns:
            values.append(_escape(record.get(column, "")))
    else:
        values.extend("" for _ in columns)
    return key_cell + "".join(f"<td>{value}</td>" for value in values)


def _render_change_rows(entry: dict[str, object]) -> str:
    key = _escape(entry.get("key"))
    changes = entry.get("changes", {})
    if not isinstance(changes, dict) or not changes:
        before = entry.get("before", {})
        after = entry.get("after", {})
        return "".join(
            f'<tr><td class="cell-key">{key}</td><td>{_escape(field)}</td>'
            f"<td>{_escape(before.get(field, ''))}</td>"
            f"<td>{_escape(after.get(field, ''))}</td></tr>"
            for field in sorted(set(before) | set(after))
        )

    rows: list[str] = []
    for field, delta in sorted(changes.items()):
        before_value = ""
        after_value = ""
        if isinstance(delta, dict):
            before_value = delta.get("before") or delta.get("from", "")
            after_value = delta.get("after") or delta.get("to", "")
        rows.append(
            "<tr>"
            f'<td class="cell-key">{key}</td>'
            f"<td>{_escape(field)}</td>"
            f"<td>{_escape(before_value)}</td>"
            f"<td>{_escape(after_value)}</td>"
            "</tr>"
        )
    return "".join(rows)


def _build_diagnostics(result: DiffResult, thresholds: dict[str, object]) -> list[str]:
    messages: list[str] = []

    violations = thresholds.get("violations") or []
    violation_map = {
        "MAX_ADDED": "Added records exceeded the configured maximum.",
        "MAX_REMOVED": "Removed records exceeded the configured maximum.",
        "UNEXPECTED_PARTNER": "Unexpected partners were found in the dataset.",
    }
    for violation in violations:
        message = violation_map.get(str(violation), f"Threshold violation: {violation}")
        messages.append(message)

    if result.unexpected_partners:
        partners = ", ".join(str(partner) for partner in result.unexpected_partners)
        messages.append(f"Unexpected partners detected: {partners}")

    duplicates = result.meta.get("duplicates_resolved", {})
    if isinstance(duplicates, dict) and duplicates.get("resolved"):
        detail = duplicates.get("details") or "Fallback key applied for uniqueness."
        messages.append(f"Duplicate keys were resolved automatically ({detail}).")

    if result.meta.get("namespace_detected"):
        messages.append("XML namespaces were detected in the source documents.")

    return messages


def render_html_report(
    result: DiffResult, payload: dict[str, object], thresholds: dict[str, object]
) -> str:
    """Render a single-file HTML report for the provided diff result."""

    meta = result.meta
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    table_label = meta.get("table") or meta.get("schema") or "SER Diff"
    title = f"ser-diff report – {table_label}"

    columns = _collect_columns(result)

    before_file = meta.get("before_file")
    after_file = meta.get("after_file")
    if not before_file:
        files = meta.get("input_files", [])
        if isinstance(files, list) and files:
            first = files[0]
            if isinstance(first, dict):
                before_file = first.get("path")
    if not after_file:
        files = meta.get("input_files", [])
        if isinstance(files, list):
            for entry in files:
                if isinstance(entry, dict) and entry.get("role") == "after":
                    after_file = entry.get("path")
                    break
    partners = meta.get("partners_detected", []) or []
    expected_partners = meta.get("expected_partners", []) or []

    diagnostics = _build_diagnostics(result, thresholds)

    summary_cards = "".join(
        '<div class="summary-card">'
        f'<span class="summary-label">{label}</span>'
        f'<span class="badge">{value}</span>'
        "</div>"
        for label, value in [
            ("Added", summary.get("added", 0)),
            ("Removed", summary.get("removed", 0)),
            ("Changed", summary.get("changed", summary.get("updated", 0))),
            ("Before rows", summary.get("total_before", 0)),
            ("After rows", summary.get("total_after", 0)),
        ]
    )

    threshold_badges = []
    if thresholds.get("max_added") is not None:
        threshold_badges.append(
            f'<div class="summary-card"><span class="summary-label">Max added</span>'
            f"<span class=\"badge badge-muted\">{thresholds['max_added']}</span></div>"
        )
    if thresholds.get("max_removed") is not None:
        threshold_badges.append(
            f'<div class="summary-card"><span class="summary-label">Max removed</span>'
            f"<span class=\"badge badge-muted\">{thresholds['max_removed']}</span></div>"
        )
    if thresholds.get("violations"):
        threshold_badges.append(
            '<div class="summary-card alert"><span class="summary-label">Violations</span>'
            f"<span class=\"badge badge-alert\">{len(thresholds['violations'])}</span></div>"
        )

    header_rows = [
        ("Before file", before_file or ""),
        ("After file", after_file or ""),
        ("Generated at", meta.get("generated_at", "")),
        ("Tool version", meta.get("tool_version", "")),
        ("Schema", meta.get("schema", "")),
        ("Key fields", ", ".join(meta.get("key_fields_used", [])) or "n/a"),
        ("Record path", meta.get("record_path", "")),
        ("Record localname", meta.get("record_localname", "")),
        ("Jira ticket", meta.get("jira", "")),
    ]

    partner_section = (
        "".join('<div class="chip">' + _escape(partner) + "</div>" for partner in partners)
        or "<em>None detected</em>"
    )

    expected_section = (
        "".join(
            '<div class="chip muted">' + _escape(partner) + "</div>"
            for partner in expected_partners
        )
        or "<em>Not configured</em>"
    )

    added_rows = "".join(
        f"<tr>{_render_record_row(entry, columns, record_key='after')}</tr>"
        for entry in result.added
    )
    removed_rows = "".join(
        f"<tr>{_render_record_row(entry, columns, record_key='before')}</tr>"
        for entry in result.removed
    )
    changed_rows = "".join(_render_change_rows(entry) for entry in result.updated)

    added_empty = f'<tr><td colspan="{len(columns) + 1}"><em>No added records.</em></td></tr>'
    removed_empty = f'<tr><td colspan="{len(columns) + 1}"><em>No removed records.</em></td></tr>'
    changed_empty = '<tr><td colspan="4"><em>No changed fields.</em></td></tr>'

    diagnostics_block = (
        "<ul>" + "".join(f"<li>{_escape(message)}</li>" for message in diagnostics) + "</ul>"
        if diagnostics
        else "<p>No diagnostics were generated for this run.</p>"
    )

    html_parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta http-equiv="Content-Security-Policy" '
        "content=\"default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'\">",
        f"  <title>{_escape(title)}</title>",
        "  <style>",
        "    :root { color-scheme: light dark; font-family: 'Inter', 'Segoe UI', sans-serif; }",
        "    body { margin: 0; padding: 1.5rem; background: #f8fafc; color: #0f172a; }",
        "    h1, h2, h3 { margin: 0; font-weight: 600; }",
        "    h2 { margin-top: 2.5rem; margin-bottom: 1rem; font-size: 1.5rem; }",
        "    h3 { margin-top: 2rem; margin-bottom: 0.75rem; font-size: 1.2rem; }",
        "    p { line-height: 1.6; }",
        "    a { color: #1d4ed8; }",
        "    .container { max-width: 1200px; margin: 0 auto; }",
        "    .header { background: #1d4ed8; color: #fff; padding: 1.5rem; border-radius: 1rem; }",
        "    .header dl { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.75rem; margin: 1.5rem 0 0; }",
        "    .header dt { font-weight: 700; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em; opacity: 0.8; }",
        "    .header dd { margin: 0; font-size: 0.95rem; }",
        "    .summary-grid { display: flex; flex-wrap: wrap; gap: 1rem; }",
        "    .summary-card { background: #fff; border-radius: 0.75rem; padding: 1rem 1.25rem; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.12); min-width: 160px; }",
        "    .summary-card.alert { background: #fee2e2; }",
        "    .summary-label { display: block; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: #475569; margin-bottom: 0.5rem; }",
        "    .badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 999px; font-weight: 600; background: #1d4ed8; color: #fff; }",
        "    .badge-muted { background: #e2e8f0; color: #1e293b; }",
        "    .badge-alert { background: #b91c1c; }",
        "    .chip { display: inline-flex; align-items: center; padding: 0.25rem 0.75rem; border-radius: 999px; background: #e0f2fe; color: #0369a1; font-size: 0.85rem; margin: 0.25rem; }",
        "    .chip.muted { background: #e2e8f0; color: #475569; }",
        "    .section { margin-top: 2.5rem; }",
        "    table { width: 100%; border-collapse: collapse; margin-top: 0.75rem; background: #fff; border-radius: 0.75rem; overflow: hidden; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08); }",
        "    table caption { text-align: left; font-weight: 600; padding: 1rem 1.25rem 0; font-size: 1.1rem; }",
        "    th, td { padding: 0.6rem 0.75rem; border-bottom: 1px solid #e2e8f0; text-align: left; vertical-align: top; }",
        "    thead th { position: sticky; top: 0; background: #f1f5f9; z-index: 2; cursor: pointer; }",
        "    tbody tr:nth-child(odd) { background: rgba(241, 245, 249, 0.5); }",
        "    .table-wrapper { overflow-x: auto; border-radius: 0.75rem; }",
        "    .table-controls { display: flex; justify-content: flex-end; margin-top: 0.5rem; }",
        "    .table-controls input { padding: 0.4rem 0.6rem; border-radius: 0.5rem; border: 1px solid #cbd5f5; min-width: 220px; }",
        "    .cell-key { font-family: 'JetBrains Mono', 'Fira Mono', monospace; font-size: 0.85rem; white-space: nowrap; }",
        "    footer { margin: 3rem 0 1rem; text-align: center; color: #64748b; font-size: 0.85rem; }",
        "  </style>",
        "</head>",
        "<body>",
        '  <div class="container">',
        '    <header class="header">',
        "      <h1>ser-diff comparison report</h1>",
        f"      <p>Table: {_escape(table_label)}</p>",
        "      <dl>",
    ]

    for label, value in header_rows:
        html_parts.append(f"        <dt>{_escape(label)}</dt>")
        html_parts.append(f"        <dd>{_escape(value)}</dd>")

    html_parts.extend(
        [
            "      </dl>",
            "    </header>",
            '    <section class="section">',
            "      <h2>Summary</h2>",
            f'      <div class="summary-grid">{summary_cards}</div>',
        ]
    )

    if threshold_badges:
        html_parts.append(
            '      <div class="summary-grid" style="margin-top:1rem;">'
            + "".join(threshold_badges)
            + "</div>"
        )

    html_parts.extend(
        [
            "      <h3>Partners</h3>",
            f"      <div>{partner_section}</div>",
            "      <h3>Expected partners</h3>",
            f"      <div>{expected_section}</div>",
            "    </section>",
        ]
    )

    html_parts.extend(
        [
            '    <section class="section">',
            "      <h2>Added records</h2>",
            '      <div class="table-controls"><input type="search" placeholder="Filter rows..." data-table-filter="table-added"></div>',
            '      <div class="table-wrapper">',
            '        <table id="table-added" class="sortable">',
            "          <thead><tr>",
            _render_table_header(columns),
            "          </tr></thead>",
            f"          <tbody>{added_rows or added_empty}</tbody>",
            "        </table>",
            "      </div>",
            "    </section>",
        ]
    )

    html_parts.extend(
        [
            '    <section class="section">',
            "      <h2>Removed records</h2>",
            '      <div class="table-controls"><input type="search" placeholder="Filter rows..." data-table-filter="table-removed"></div>',
            '      <div class="table-wrapper">',
            '        <table id="table-removed" class="sortable">',
            "          <thead><tr>",
            _render_table_header(columns),
            "          </tr></thead>",
            f"          <tbody>{removed_rows or removed_empty}</tbody>",
            "        </table>",
            "      </div>",
            "    </section>",
        ]
    )

    html_parts.extend(
        [
            '    <section class="section">',
            "      <h2>Changed fields</h2>",
            '      <div class="table-controls"><input type="search" placeholder="Filter rows..." data-table-filter="table-changed"></div>',
            '      <div class="table-wrapper">',
            '        <table id="table-changed" class="sortable">',
            '          <thead><tr><th scope="col">Key</th><th scope="col">Field</th><th scope="col">Before</th><th scope="col">After</th></tr></thead>',
            f"          <tbody>{changed_rows or changed_empty}</tbody>",
            "        </table>",
            "      </div>",
            "    </section>",
        ]
    )

    html_parts.extend(
        [
            '    <section class="section">',
            "      <h2>Diagnostics</h2>",
            f"      {diagnostics_block}",
            "    </section>",
            "    <footer>Generated by ser-diff. View canonical payload via the embedded JSON script tag.</footer>",
        ]
    )

    html_parts.extend(
        [
            "  </div>",
            f'  <script type="application/json" id="ser-diff-data">{safe_json_for_script(payload)}</script>',
            "  <script>",
            "    (function() {",
            "      const dataEl = document.getElementById('ser-diff-data');",
            "      if (dataEl) {",
            "        try {",
            "          window.serDiffPayload = JSON.parse(dataEl.textContent);",
            "        } catch (error) {",
            "          console.error('Failed to parse embedded payload', error);",
            "        }",
            "      }",
            "      const filters = document.querySelectorAll('[data-table-filter]');",
            "      filters.forEach((input) => {",
            "        input.addEventListener('input', () => {",
            "          const targetId = input.getAttribute('data-table-filter');",
            "          const term = input.value.trim().toLowerCase();",
            "          const table = document.getElementById(targetId);",
            "          if (!table) { return; }",
            "          table.querySelectorAll('tbody tr').forEach((row) => {",
            "            const text = row.textContent.toLowerCase();",
            "            row.style.display = term === '' || text.includes(term) ? '' : 'none';",
            "          });",
            "        });",
            "      });",
            "      document.querySelectorAll('table.sortable thead th').forEach((th, index) => {",
            "        th.addEventListener('click', () => {",
            "          const table = th.closest('table');",
            "          const tbody = table.querySelector('tbody');",
            "          const rows = Array.from(tbody.querySelectorAll('tr'));",
            "          const ascending = th.dataset.sort !== 'asc';",
            "          rows.sort((a, b) => {",
            "            const av = a.children[index].textContent.trim();",
            "            const bv = b.children[index].textContent.trim();",
            "            const aNum = Number(av.replace(/[^0-9.-]+/g, ''));",
            "            const bNum = Number(bv.replace(/[^0-9.-]+/g, ''));",
            "            if (!Number.isNaN(aNum) && !Number.isNaN(bNum)) {",
            "              return ascending ? aNum - bNum : bNum - aNum;",
            "            }",
            "            return ascending ? av.localeCompare(bv) : bv.localeCompare(av);",
            "          });",
            "          rows.forEach((row) => tbody.appendChild(row));",
            "          table.querySelectorAll('th').forEach((header) => { header.dataset.sort = ''; });",
            "          th.dataset.sort = ascending ? 'asc' : 'desc';",
            "        });",
            "      });",
            "    })();",
            "  </script>",
            "</body>",
            "</html>",
        ]
    )

    return "\n".join(html_parts)
