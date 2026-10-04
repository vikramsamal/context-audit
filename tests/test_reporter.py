"""Tests for terminal and JSON reporters."""

from __future__ import annotations

import json
from pathlib import Path

from context_audit.analyzer import AuditAnalyzer
from context_audit.reporter import JsonReporter, TerminalReporter, format_bytes


def test_format_bytes():
    assert format_bytes(500) == "500 B"
    assert format_bytes(1024) == "1.00 KB"
    assert format_bytes(1024 * 1024) == "1.00 MB"
    assert format_bytes(1024 * 1024 * 1024) == "1.00 GB"


def test_terminal_reporter(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "package-lock.json").write_text('{"name": "test"}\n', encoding="utf-8")

    analyzer = AuditAnalyzer(str(tmp_path))
    report = analyzer.analyze()

    reporter = TerminalReporter(color=False, top_n=5)
    output = reporter.render(report)

    assert "Context Audit" in output
    assert "Files scanned:" in output
    assert "Estimated tokens:" in output
    assert "Potentially unnecessary:" in output
    assert "Potential useful context:" in output
    assert "Top context-heavy files" in output
    assert "Suggested next step" in output
    assert "No files were modified." in output
    assert "No data was uploaded." in output


def test_json_reporter(tmp_path: Path):
    (tmp_path / "app.ts").write_text("const x = 1;\n", encoding="utf-8")
    (tmp_path / "data.json").write_text('{"key": "value"}\n', encoding="utf-8")

    analyzer = AuditAnalyzer(str(tmp_path))
    report = analyzer.analyze()

    reporter = JsonReporter()
    json_str = reporter.render(report)

    data = json.loads(json_str)
    assert data["files_scanned"] == 2
    assert data["text_files"] == 2
    assert "estimated_tokens" in data
    assert "largest_files" in data
    assert "potentially_unnecessary" in data
    assert "warnings" in data
    assert isinstance(data["largest_files"], list)
