"""Safety and read-only verification tests.

Validates that context-audit NEVER:
- Modifies user files
- Deletes user files
- Creates new files inside the target directory
- Performs network calls
- Spawns external subprocesses
"""

from __future__ import annotations

import hashlib
import socket
import subprocess
from pathlib import Path

import pytest

from context_audit.analyzer import AuditAnalyzer
from context_audit.cli import main


def get_directory_state(root_path: Path) -> dict[str, tuple[str, int, int]]:
    """Compute (sha256, size_bytes, mtime_ns) for all files in root_path."""
    state = {}
    for p in root_path.rglob("*"):
        if p.is_file() and not p.is_symlink():
            content = p.read_bytes()
            sha = hashlib.sha256(content).hexdigest()
            st = p.stat()
            state[str(p)] = (sha, st.st_size, st.st_mtime_ns)
    return state


def test_safety_no_files_modified_or_deleted(tmp_path: Path):
    # Setup test repository structure
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("def run(): pass\n", encoding="utf-8")
    (src / "generated.ts").write_text("// @generated\nexport const X = 1;\n", encoding="utf-8")
    (tmp_path / "package-lock.json").write_text('{"lockfileVersion": 2}\n', encoding="utf-8")
    (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02\x03")

    state_before = get_directory_state(tmp_path)
    assert len(state_before) == 4

    # Run analysis
    analyzer = AuditAnalyzer(str(tmp_path))
    report = analyzer.analyze()
    assert report.files_scanned >= 4

    # Run CLI
    exit_code = main([str(tmp_path), "--json"])
    assert exit_code == 0

    state_after = get_directory_state(tmp_path)

    # Assert exactly the same files exist with identical hashes and sizes
    assert set(state_before.keys()) == set(state_after.keys())
    for file_path, (sha_before, size_before, mtime_before) in state_before.items():
        sha_after, size_after, mtime_after = state_after[file_path]
        assert sha_before == sha_after, f"File {file_path} content hash changed!"
        assert size_before == size_after, f"File {file_path} size changed!"
        assert mtime_before == mtime_after, f"File {file_path} mtime changed!"


def test_safety_no_network_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "index.py").write_text("print('safe')", encoding="utf-8")

    # Block socket connections
    def fake_socket(*args, **kwargs):
        raise RuntimeError("Network calls are forbidden in context-audit!")

    monkeypatch.setattr(socket, "socket", fake_socket)

    # Should run smoothly offline without network
    analyzer = AuditAnalyzer(str(tmp_path))
    report = analyzer.analyze()
    assert report.files_scanned == 1


def test_safety_no_subprocesses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "index.py").write_text("print('safe')", encoding="utf-8")

    def fake_subprocess(*args, **kwargs):
        raise RuntimeError("Subprocesses are forbidden during normal scan in context-audit!")

    monkeypatch.setattr(subprocess, "Popen", fake_subprocess)
    monkeypatch.setattr(subprocess, "run", fake_subprocess)
    monkeypatch.setattr(subprocess, "call", fake_subprocess)

    # Should run smoothly in pure Python
    analyzer = AuditAnalyzer(str(tmp_path))
    report = analyzer.analyze()
    assert report.files_scanned == 1
