"""Tests for configuration loading and CLI overrides."""

from __future__ import annotations

import textwrap
from pathlib import Path

from serdiff import cli
from serdiff.config import load_config


def test_load_config_precedence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    (tmp_path / ".serdiff.json").write_text('{"jira": {"ticket": "JSON"}}', encoding="utf-8")
    (tmp_path / ".serdiff.yaml").write_text("jira:\n  ticket: YAML", encoding="utf-8")
    (tmp_path / ".serdiff.toml").write_text("[jira]\nticket = 'TOML'\n", encoding="utf-8")

    loaded = load_config(Path.cwd())

    assert loaded.path == tmp_path / ".serdiff.toml"
    assert loaded.data["jira"]["ticket"] == "TOML"


def test_cli_config_application_and_override(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    config_content = textwrap.dedent(
        """
        [jira]
        ticket = "SER-1234"

        [io]
        output_dir = "configured-reports"
        out_prefix = "configured"

        [guards]
        expected_partners = ["Alpha", "Beta"]
        max_added = 5
        max_removed = 2
        fail_on_unexpected = true

        [preset]
        mode = "custom"

        [custom]
        record_path = "./Custom"
        record_localname = "Custom"
        keys = ["Id"]
        fields = ["Id", "Name"]
        strip_ns = true
        """
    ).strip()

    (tmp_path / ".serdiff.toml").write_text(config_content + "\n", encoding="utf-8")

    base_args = cli._parse_args(["--before", "before.xml", "--after", "after.xml"])
    loaded = load_config(Path.cwd())
    merged = cli._merge_cli_with_config(base_args, loaded)

    assert merged.jira == "SER-1234"
    assert merged.output_dir == "configured-reports"
    assert merged.out_prefix == "configured"
    assert merged.expected_partners == "Alpha, Beta"
    assert merged.max_added == 5
    assert merged.max_removed == 2
    assert merged.fail_on_unexpected is True
    assert merged.record_path == "./Custom"
    assert merged.record_localname == "Custom"
    assert merged.keys == ["Id"]
    assert merged.fields == "Id, Name"
    assert merged.strip_ns is True
    assert merged.auto is False

    override_args = cli._parse_args(
        [
            "--before",
            "before.xml",
            "--after",
            "after.xml",
            "--output-dir",
            "cli-reports",
            "--no-fail-on-unexpected",
        ]
    )
    override_merged = cli._merge_cli_with_config(override_args, loaded)

    assert override_merged.output_dir == "cli-reports"
    assert override_merged.fail_on_unexpected is False


def test_init_creates_template_and_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    first_exit = cli.main(["init"])
    config_path = tmp_path / ".serdiff.toml"
    assert first_exit == cli.EXIT_SUCCESS
    assert config_path.exists()

    content_first = config_path.read_text(encoding="utf-8")
    assert "# ser-diff configuration template" in content_first
    assert '# out_prefix = "diff_report"' in content_first
    assert str((tmp_path / "reports").resolve()) in content_first

    second_exit = cli.main(["init"])
    content_second = config_path.read_text(encoding="utf-8")

    assert second_exit == cli.EXIT_SUCCESS
    assert content_first == content_second
