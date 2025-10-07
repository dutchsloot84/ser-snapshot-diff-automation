"""Tkinter GUI wrapper for the ser-diff engine."""

from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from serdiff.entrypoints import DiffRunResult, run_diff, run_doctor
from serdiff.gui_utils import (
    get_default_output_dir,
    get_last_directory,
    load_prefill_jira_ticket,
    open_path,
    remember_last_directory,
)

HEADLESS = os.getenv("SERDIFF_GUI_HEADLESS") == "1"


class StatusBanner(tk.Label):
    """Small helper to display status messages with colours."""

    COLORS = {"info": "#0A6F4E", "warn": "#B45F06", "idle": "#444444"}

    def show(
        self, message: str, *, kind: str = "info"
    ) -> None:  # pragma: no cover - Tk side effect
        self.config(text=message, foreground=self.COLORS.get(kind, self.COLORS["info"]))


def _validate_file(path: str) -> bool:
    return bool(path) and Path(path).expanduser().is_file()


def _build_filetypes() -> list[tuple[str, str]]:
    return [("XML files", "*.xml"), ("All files", "*.*")]


def _select_file(variable: tk.StringVar) -> None:  # pragma: no cover - Tk side effect
    initial_dir = get_last_directory() or Path.home()
    filename = filedialog.askopenfilename(
        title="Select XML file",
        initialdir=str(initial_dir),
        filetypes=_build_filetypes(),
    )
    if filename:
        variable.set(filename)
        remember_last_directory(filename)


def _update_run_state(button: tk.Button, before: tk.StringVar, after: tk.StringVar) -> None:
    valid = _validate_file(before.get()) and _validate_file(after.get())
    button.config(state=tk.NORMAL if valid else tk.DISABLED)


def _handle_result(result: DiffRunResult, status: StatusBanner) -> None:
    opened_target = False
    try:
        if result.primary_report and Path(result.primary_report).exists():
            open_path(result.primary_report)
            opened_target = True
        elif result.output_dir and Path(result.output_dir).is_dir():
            open_path(result.output_dir)
            opened_target = True
        else:
            candidate: Path | None = None
            if result.primary_report:
                candidate = Path(result.primary_report).expanduser().parent
            elif result.output_dir:
                candidate = Path(result.output_dir).expanduser().parent
            if candidate and candidate.exists():
                open_path(candidate)
                opened_target = True
    except Exception as exc:  # pragma: no cover - defensive guard
        messagebox.showwarning("Could not open report", str(exc))
    else:
        if not opened_target:
            messagebox.showwarning(
                "Could not open report",
                "Report generated but could not be opened automatically.",
            )

    if result.exit_code != 0:
        status.show(
            "Guardrails triggered; see Summary in the report.",
            kind="warn",
        )
        messagebox.showwarning(
            "Guardrails triggered", "Report generated; guardrails fired. Review the Summary tab."
        )
    else:
        status.show("Reports created", kind="info")
        suffix = " The output was opened in your file browser." if opened_target else ""
        messagebox.showinfo("Reports created", f"Report generated.{suffix}")


def _run_doctor_dialog(status: StatusBanner) -> None:  # pragma: no cover - Tk side effect
    try:
        exit_code, output = run_doctor()
    except Exception as exc:  # pragma: no cover - defensive guard
        messagebox.showerror("Doctor failed", str(exc))
        return

    if exit_code == 0:
        messagebox.showinfo("Environment OK", output or "All checks passed.")
        status.show("Environment checks succeeded", kind="info")
    else:
        messagebox.showwarning(
            "Environment issues detected", output or "See console output for details."
        )
        status.show("Environment issues detected", kind="warn")


def _build_row(
    master: tk.Widget, label: str, variable: tk.StringVar, *, with_button: bool = True
) -> None:
    frame = tk.Frame(master)
    frame.pack(fill=tk.X, padx=12, pady=6)

    tk.Label(frame, text=label, width=14, anchor="w").pack(side=tk.LEFT)
    entry = tk.Entry(frame, textvariable=variable, width=60)
    entry.pack(side=tk.LEFT, padx=6)

    if with_button:
        browse = tk.Button(frame, text="Browse…", command=lambda: _select_file(variable))
        browse.pack(side=tk.LEFT)


def main() -> tk.Tk | None:  # pragma: no cover - UI wiring is hard to deterministically test
    root = tk.Tk()
    root.title("SER Diff")
    root.resizable(False, False)

    status = StatusBanner(root, text="", anchor="w")
    status.pack(fill=tk.X, padx=12, pady=(8, 0))
    status.show("Pick BEFORE and AFTER XML files to begin.", kind="idle")

    before_var = tk.StringVar(master=root)
    after_var = tk.StringVar(master=root)
    jira_default = load_prefill_jira_ticket() or ""
    jira_var = tk.StringVar(master=root, value=jira_default)

    _build_row(root, "BEFORE XML", before_var)
    _build_row(root, "AFTER XML", after_var)
    _build_row(root, "Jira ID (opt.)", jira_var, with_button=False)

    button_row = tk.Frame(root)
    button_row.pack(fill=tk.X, padx=12, pady=12)

    run_button = tk.Button(button_row, text="Run Diff", state=tk.DISABLED)
    run_button.pack(side=tk.RIGHT)

    env_button = tk.Button(
        button_row, text="Check Environment", command=lambda: _run_doctor_dialog(status)
    )
    env_button.pack(side=tk.LEFT)

    def trigger_update(*_: object) -> None:
        _update_run_state(run_button, before_var, after_var)

    before_var.trace_add("write", trigger_update)
    after_var.trace_add("write", trigger_update)

    def run_diff_action() -> None:
        before = before_var.get().strip()
        after = after_var.get().strip()

        if not (_validate_file(before) and _validate_file(after)):
            messagebox.showwarning(
                "Missing files", "Please select valid BEFORE and AFTER XML files."
            )
            return

        try:
            output_dir = get_default_output_dir()
        except OSError as exc:
            messagebox.showerror("Output directory", f"Unable to create reports directory: {exc}")
            return

        try:
            result = run_diff(
                before=before,
                after=after,
                jira=jira_var.get().strip() or None,
                report="html",
                output_dir=output_dir,
            )
        except FileNotFoundError as exc:
            messagebox.showerror("File not found", str(exc))
            return
        except Exception as exc:  # pragma: no cover - defensive guard
            messagebox.showerror("Run failed", str(exc))
            return

        remember_last_directory(before)
        remember_last_directory(after)
        _handle_result(result, status)
        trigger_update()

    run_button.config(command=run_diff_action)

    if HEADLESS:
        root.update_idletasks()
        root.destroy()
        return root

    root.mainloop()
    return root


if __name__ == "__main__":  # pragma: no cover
    main()
