"""Tests for audit analyzer and aggregation."""

from __future__ import annotations

from pathlib import Path

from context_audit.analyzer import AuditAnalyzer


def test_analyzer_on_clean_project(tmp_path: Path):
    (tmp_path / "app.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# My Project\n\nDocs here.", encoding="utf-8")

    analyzer = AuditAnalyzer(str(tmp_path))
    report = analyzer.analyze()

    assert report.files_scanned == 2
    assert report.text_files_count == 2
    assert report.binary_files_skipped == 0
    assert report.total_estimated_tokens > 0
    assert report.potentially_unnecessary_tokens == 0
    assert report.potential_useful_tokens == report.total_estimated_tokens
    assert len(report.file_types) == 2


def test_analyzer_duplicate_file_detection(tmp_path: Path):
    content = "import os\nimport sys\n\ndef run():\n    pass\n" * 10
    (tmp_path / "file1.py").write_text(content, encoding="utf-8")
    (tmp_path / "file1_copy.py").write_text(content, encoding="utf-8")
    (tmp_path / "file1_backup.py").write_text(content, encoding="utf-8")

    analyzer = AuditAnalyzer(str(tmp_path))
    report = analyzer.analyze()

    assert len(report.duplicate_groups) == 1
    dup_group = report.duplicate_groups[0]
    assert len(dup_group.files) == 3
    assert dup_group.wasted_tokens > 0
    assert report.total_duplicate_wasted_tokens == dup_group.wasted_tokens
    # Duplicates should be reflected in potentially unnecessary tokens
    assert report.potentially_unnecessary_tokens >= dup_group.wasted_tokens


def test_analyzer_file_type_breakdown(tmp_path: Path):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / "c.js").write_text("const z = 3;\n", encoding="utf-8")

    analyzer = AuditAnalyzer(str(tmp_path))
    report = analyzer.analyze()

    exts = [ft.extension for ft in report.file_types]
    assert ".py" in exts
    assert ".js" in exts

    py_summary = next(ft for ft in report.file_types if ft.extension == ".py")
    assert py_summary.file_count == 2


def test_analyzer_rankings(tmp_path: Path):
    (tmp_path / "small.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "medium.py").write_text("print('hello world')\n" * 10, encoding="utf-8")
    (tmp_path / "large.py").write_text("data = [1, 2, 3]\n" * 100, encoding="utf-8")

    analyzer = AuditAnalyzer(str(tmp_path))
    report = analyzer.analyze()

    assert len(report.top_files_by_tokens) == 3
    assert report.top_files_by_tokens[0].relative_path == "large.py"
    assert report.top_files_by_tokens[1].relative_path == "medium.py"
    assert report.top_files_by_tokens[2].relative_path == "small.py"
