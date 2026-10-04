"""Tests for CLI arguments, parsing, and execution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from context_audit.cli import main


def test_cli_default_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    (tmp_path / "hello.py").write_text("print('hello world')\n", encoding="utf-8")

    exit_code = main([str(tmp_path)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "Context Audit" in captured.out
    assert "Files scanned:" in captured.out


def test_cli_json_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    (tmp_path / "index.js").write_text("console.log('hi');\n", encoding="utf-8")

    exit_code = main([str(tmp_path), "--json"])
    assert exit_code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["files_scanned"] == 1
    assert data["text_files"] == 1


def test_cli_nonexistent_directory(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    fake_path = tmp_path / "nonexistent_dir"
    exit_code = main([str(fake_path)])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "Error:" in captured.err


def test_cli_top_n_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    for i in range(15):
        (tmp_path / f"file_{i}.py").write_text(f"x = {i}\n", encoding="utf-8")

    exit_code = main([str(tmp_path), "--top", "5", "--no-color"])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "Top context-heavy files" in captured.out


def test_cli_no_color_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    (tmp_path / "app.py").write_text("print('test')\n", encoding="utf-8")

    exit_code = main([str(tmp_path), "--no-color"])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "\033[" not in captured.out
