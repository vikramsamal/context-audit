"""Tests for safe filesystem scanner."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from context_audit.scanner import Scanner, is_binary_file


def test_scanner_nonexistent_directory(tmp_path: Path):
    nonexistent = tmp_path / "does_not_exist"
    scanner = Scanner(str(nonexistent))
    with pytest.raises(FileNotFoundError):
        list(scanner.scan())


def test_scanner_empty_directory(tmp_path: Path):
    scanner = Scanner(str(tmp_path))
    results = list(scanner.scan())
    assert len(results) == 0


def test_scanner_normal_text_files(tmp_path: Path):
    file1 = tmp_path / "main.py"
    file1.write_text("print('hello world')\n", encoding="utf-8")

    sub = tmp_path / "pkg"
    sub.mkdir()
    file2 = sub / "utils.py"
    file2.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    scanner = Scanner(str(tmp_path))
    results = list(scanner.scan())
    assert len(results) == 2

    paths = {info.relative_path for info, _ in results}
    assert "main.py" in paths
    assert os.path.join("pkg", "utils.py") in paths or "pkg/utils.py" in paths

    for info, _ in results:
        assert not info.is_binary
        assert not info.is_unreadable
        assert info.char_count > 0
        assert info.line_count > 0


def test_scanner_binary_files(tmp_path: Path):
    # Binary by null byte
    bin_file = tmp_path / "data.bin"
    bin_file.write_bytes(b"\x00\x01\x02\x03\x04")

    # Binary by extension
    png_file = tmp_path / "image.png"
    png_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")

    scanner = Scanner(str(tmp_path))
    results = list(scanner.scan())
    assert len(results) == 2

    for info, _ in results:
        assert info.is_binary


def test_is_binary_file_helper():
    assert is_binary_file("test.png", b"") is True
    assert is_binary_file("test.txt", b"hello world\x00extra") is True
    assert is_binary_file("test.py", b"def hello(): pass\n") is False


def test_scanner_ignores_git_directory(tmp_path: Path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("git config here", encoding="utf-8")
    (tmp_path / "app.py").write_text("print('app')", encoding="utf-8")

    scanner = Scanner(str(tmp_path))
    results = list(scanner.scan())
    assert len(results) == 1
    assert results[0][0].relative_path == "app.py"


def test_scanner_respects_default_ignored_dirs(tmp_path: Path):
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    (venv_dir / "lib.py").write_text("import sys", encoding="utf-8")

    nm_dir = tmp_path / "node_modules"
    nm_dir.mkdir()
    (nm_dir / "index.js").write_text("module.exports = {}", encoding="utf-8")

    (tmp_path / "index.ts").write_text("console.log('hi');", encoding="utf-8")

    # With default ignore enabled:
    scanner = Scanner(str(tmp_path), skip_default_ignored=True)
    results = list(scanner.scan())
    assert len(results) == 1
    assert results[0][0].relative_path == "index.ts"

    # With default ignore disabled (--all):
    scanner_all = Scanner(str(tmp_path), skip_default_ignored=False)
    results_all = list(scanner_all.scan())
    assert len(results_all) == 3


def test_scanner_gitignore_support(tmp_path: Path):
    gitignore_content = "*.tmp\n/secret.json\nbuild/\n!build/keep.txt\n"
    (tmp_path / ".gitignore").write_text(gitignore_content, encoding="utf-8")

    (tmp_path / "file.tmp").write_text("temporary", encoding="utf-8")
    (tmp_path / "secret.json").write_text("{}", encoding="utf-8")
    (tmp_path / "main.go").write_text("package main", encoding="utf-8")

    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "out.txt").write_text("build output", encoding="utf-8")
    (build_dir / "keep.txt").write_text("keep this", encoding="utf-8")

    scanner = Scanner(str(tmp_path), respect_gitignore=True, skip_default_ignored=False)
    results = list(scanner.scan())
    rel_paths = {info.relative_path.replace("\\", "/") for info, _ in results}

    assert "main.go" in rel_paths
    assert ".gitignore" in rel_paths
    assert "file.tmp" not in rel_paths
    assert "secret.json" not in rel_paths
    assert "build/out.txt" not in rel_paths


def test_scanner_single_file(tmp_path: Path):
    file_path = tmp_path / "standalone.py"
    file_path.write_text("x = 42\n", encoding="utf-8")

    scanner = Scanner(str(file_path))
    results = list(scanner.scan())
    assert len(results) == 1
    info, _ = results[0]
    assert info.relative_path == "standalone.py"
    assert info.line_count == 1


def test_scanner_handles_symlink_safety(tmp_path: Path):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "doc.txt").write_text("real content", encoding="utf-8")

    # Create symlink pointing to real_dir (if OS permits)
    link_dir = tmp_path / "link"
    try:
        os.symlink(str(real_dir), str(link_dir))
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this platform/filesystem")

    scanner = Scanner(str(tmp_path))
    results = list(scanner.scan())
    # Should safely scan without infinite recursion or errors
    assert len(results) >= 1


def test_scanner_unreadable_file(tmp_path: Path):
    unreadable = tmp_path / "locked.txt"
    unreadable.write_text("secret content", encoding="utf-8")
    try:
        os.chmod(str(unreadable), 0o000)
    except OSError:
        pytest.skip("Chmod not supported on this OS")

    scanner = Scanner(str(tmp_path))
    try:
        results = list(scanner.scan())
        # If the OS enforces 000 permissions
        if results:
            info, _ = results[0]
            if info.is_unreadable:
                assert info.error_message is not None
    finally:
        os.chmod(str(unreadable), 0o644)


def test_scanner_oversized_file_streaming(tmp_path: Path):
    large_file = tmp_path / "large.txt"
    large_file.write_text("line of content\n" * 100, encoding="utf-8")

    # Set max_file_size to 200 bytes so streaming path is triggered
    scanner = Scanner(str(tmp_path), max_file_size=200)
    results = list(scanner.scan())
    assert len(results) == 1
    info, sample = results[0]
    assert info.size_bytes > 200
    assert info.content_hash is not None
    assert len(sample) > 0
