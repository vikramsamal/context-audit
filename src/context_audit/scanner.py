"""Safe filesystem scanner for context-audit.

Performs recursive, read-only scanning of project directories, safely handling
symlinks, permissions, binary detection, and .gitignore rules.
"""

from __future__ import annotations

import fnmatch
import hashlib
import os
from typing import TYPE_CHECKING

from context_audit.models import FileInfo

if TYPE_CHECKING:
    from collections.abc import Iterator

# Common binary file extensions to immediately classify as binary
KNOWN_BINARY_EXTENSIONS: set[str] = {
    # Images
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".bmp",
    ".tiff",
    ".psd",
    ".raw",
    # Audio / Video
    ".mp3",
    ".mp4",
    ".wav",
    ".ogg",
    ".flac",
    ".avi",
    ".mov",
    ".mkv",
    ".webm",
    # Archives / Compressed
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".tgz",
    ".jar",
    ".war",
    # Compiled / Binaries / Libraries
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".obj",
    ".o",
    ".a",
    ".lib",
    ".pyc",
    ".pyo",
    ".pyd",
    ".class",
    ".wasm",
    # Fonts
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    # Documents / Binary formats
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    # Data / Databases
    ".parquet",
    ".avro",
    ".orc",
    ".db",
    ".sqlite",
    ".sqlite3",
}

# Directories always ignored by default for performance and safety
ALWAYS_IGNORE_DIRS: set[str] = {
    ".git",
    ".hg",
    ".svn",
}

# Directories ignored by default (unless --all is specified)
DEFAULT_IGNORE_DIRS: set[str] = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    ".nuxt",
    ".turbo",
    "dist",
    "build",
    "target",
    "coverage",
    ".cache",
}

# Buffer size for reading initial chunk to detect binary / headers
INITIAL_BUFFER_SIZE: int = 8192

# Max file size for full content hashing / reading (50 MB)
MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024


class GitIgnoreRule:
    """Represents a single parsed rule from a .gitignore file."""

    def __init__(self, pattern: str, base_dir: str):
        self.raw_pattern = pattern
        self.base_dir = os.path.abspath(base_dir).replace("\\", "/")
        self.is_negation = pattern.startswith("!")
        if self.is_negation:
            pattern = pattern[1:]

        self.dir_only = pattern.endswith("/")
        if self.dir_only:
            pattern = pattern[:-1]

        self.anchored = "/" in pattern.rstrip("/")
        if pattern.startswith("/"):
            pattern = pattern[1:]
            self.anchored = True

        self.pattern = pattern

    def matches(self, abs_path: str, is_dir: bool) -> bool:
        """Check if an absolute path matches this gitignore rule."""
        norm_path = abs_path.replace("\\", "/")
        if not norm_path.startswith(self.base_dir):
            return False

        rel_path = norm_path[len(self.base_dir) :].lstrip("/")
        if not rel_path:
            return False

        if self.dir_only and not is_dir:
            return False

        if self.anchored:
            # Match from base_dir directly
            if fnmatch.fnmatch(rel_path, self.pattern):
                return True
            if fnmatch.fnmatch(rel_path, self.pattern + "/*"):
                return True
        else:
            # Match anywhere in path or against basename
            parts = rel_path.split("/")
            for i in range(len(parts)):
                sub_path = "/".join(parts[i:])
                if fnmatch.fnmatch(sub_path, self.pattern):
                    return True
                if fnmatch.fnmatch(parts[i], self.pattern):
                    return True

        return False


class GitIgnoreParser:
    """Manages hierarchical .gitignore rules across directories."""

    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)
        self.rules_by_dir: dict[str, list[GitIgnoreRule]] = {}
        self._loaded_dirs: set[str] = set()

    def load_gitignore(self, dir_path: str) -> None:
        """Load .gitignore in dir_path if present and not already loaded."""
        abs_dir = os.path.abspath(dir_path)
        if abs_dir in self._loaded_dirs:
            return
        self._loaded_dirs.add(abs_dir)

        gitignore_file = os.path.join(abs_dir, ".gitignore")
        if not os.path.isfile(gitignore_file):
            return

        rules: list[GitIgnoreRule] = []
        try:
            with open(gitignore_file, encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    rules.append(GitIgnoreRule(line, abs_dir))
        except OSError:
            pass

        if rules:
            self.rules_by_dir[abs_dir] = rules

    def is_ignored(self, abs_path: str, is_dir: bool) -> bool:
        """Check if abs_path is ignored by any applicable .gitignore rule."""
        norm_path = os.path.abspath(abs_path).replace("\\", "/")

        # Collect all rules from parent directories up to root
        matching_rules: list[GitIgnoreRule] = []
        for dir_path, rules in self.rules_by_dir.items():
            if norm_path == dir_path or norm_path.startswith(dir_path + "/"):
                matching_rules.extend(rules)

        ignored = False
        for rule in matching_rules:
            if rule.matches(norm_path, is_dir):
                ignored = not rule.is_negation

        return ignored


def is_binary_file(file_path: str, initial_bytes: bytes) -> bool:
    """Check whether a file is binary using extension and byte inspection.

    Args:
        file_path: Path to the file.
        initial_bytes: First chunk of bytes read from the file.

    Returns:
        True if the file is determined to be binary.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in KNOWN_BINARY_EXTENSIONS:
        return True

    if not initial_bytes:
        return False

    # Check for null bytes (standard heuristic used by git/diff)
    if b"\x00" in initial_bytes:
        return True

    # Check for non-text byte ratio in initial buffer
    text_characters = bytes(range(32, 127)) + b"\n\r\t\b\f"
    non_text = [b for b in initial_bytes if b not in text_characters]
    if len(non_text) / len(initial_bytes) > 0.30:
        return True

    return False


class Scanner:
    """Safe, read-only filesystem scanner for codebases."""

    def __init__(
        self,
        root_dir: str,
        respect_gitignore: bool = True,
        skip_default_ignored: bool = True,
        max_file_size: int = MAX_FILE_SIZE_BYTES,
    ):
        self.root_dir = os.path.abspath(root_dir)
        self.respect_gitignore = respect_gitignore
        self.skip_default_ignored = skip_default_ignored
        self.max_file_size = max_file_size
        self.gitignore_parser = GitIgnoreParser(self.root_dir)
        self.visited_inodes: set[tuple[int, int]] = set()

    def scan(self) -> Iterator[tuple[FileInfo, str]]:
        """Walk the directory tree and yield (FileInfo, content_sample) tuples.

        Yields:
            Tuple of (FileInfo, content_sample_string) for each encountered file.
        """
        if not os.path.exists(self.root_dir):
            raise FileNotFoundError(f"Project directory not found: {self.root_dir}")

        if os.path.isfile(self.root_dir):
            # Handle single file audit
            info, sample = self._inspect_file(self.root_dir, os.path.basename(self.root_dir))
            yield info, sample
            return

        for current_dir, dirnames, filenames in os.walk(self.root_dir, followlinks=False):
            # Safe check against cyclic symlink loops
            try:
                st = os.stat(current_dir)
                inode_key = (st.st_dev, st.st_ino)
                if inode_key in self.visited_inodes:
                    dirnames.clear()
                    continue
                self.visited_inodes.add(inode_key)
            except OSError:
                dirnames.clear()
                continue

            # Load gitignore if present in current directory
            if self.respect_gitignore:
                self.gitignore_parser.load_gitignore(current_dir)

            # Filter directory names to prevent descending into ignored directories
            filtered_dirnames = []
            for d in dirnames:
                dir_path = os.path.join(current_dir, d)

                # Always ignore .git
                if d in ALWAYS_IGNORE_DIRS:
                    continue

                # Ignore default ignored directories if enabled
                if self.skip_default_ignored and d in DEFAULT_IGNORE_DIRS:
                    continue

                # Check .gitignore
                if self.respect_gitignore and self.gitignore_parser.is_ignored(
                    dir_path, is_dir=True
                ):
                    continue

                # Check symlink safety
                if os.path.islink(dir_path):
                    try:
                        target = os.path.realpath(dir_path)
                        target_st = os.stat(target)
                        if (target_st.st_dev, target_st.st_ino) in self.visited_inodes:
                            continue
                    except OSError:
                        continue

                filtered_dirnames.append(d)

            dirnames[:] = filtered_dirnames

            # Inspect files in current directory
            for filename in filenames:
                file_path = os.path.join(current_dir, filename)
                rel_path = os.path.relpath(file_path, self.root_dir)

                # Check if ignored by .gitignore
                if self.respect_gitignore and self.gitignore_parser.is_ignored(
                    file_path, is_dir=False
                ):
                    continue

                info, content_sample = self._inspect_file(file_path, rel_path)
                yield info, content_sample

    def _inspect_file(self, file_path: str, rel_path: str) -> tuple[FileInfo, str]:
        """Inspect a single file safely and gather metrics without modifying it."""
        ext = os.path.splitext(file_path)[1].lower() or "(no ext)"
        is_symlink = os.path.islink(file_path)

        try:
            stat_info = os.lstat(file_path) if is_symlink else os.stat(file_path)
            size_bytes = stat_info.st_size
        except OSError as e:
            return (
                FileInfo(
                    path=file_path,
                    relative_path=rel_path,
                    extension=ext,
                    size_bytes=0,
                    is_unreadable=True,
                    is_symlink=is_symlink,
                    error_message=str(e),
                ),
                "",
            )

        # If it's a broken symlink
        if is_symlink and not os.path.exists(file_path):
            return (
                FileInfo(
                    path=file_path,
                    relative_path=rel_path,
                    extension=ext,
                    size_bytes=size_bytes,
                    is_symlink=True,
                    is_unreadable=True,
                    error_message="Broken symbolic link",
                ),
                "",
            )

        # Handle empty files
        if size_bytes == 0:
            return (
                FileInfo(
                    path=file_path,
                    relative_path=rel_path,
                    extension=ext,
                    size_bytes=0,
                    char_count=0,
                    line_count=0,
                    estimated_tokens=0,
                    content_hash=hashlib.sha256(b"").hexdigest(),
                ),
                "",
            )

        # Read initial buffer to detect binary & compute hash
        try:
            with open(file_path, "rb") as f:
                initial_bytes = f.read(INITIAL_BUFFER_SIZE)
                if is_binary_file(file_path, initial_bytes):
                    return (
                        FileInfo(
                            path=file_path,
                            relative_path=rel_path,
                            extension=ext,
                            size_bytes=size_bytes,
                            is_binary=True,
                            is_symlink=is_symlink,
                        ),
                        "",
                    )

                # For text files, calculate sha256 hash using chunked streaming
                hasher = hashlib.sha256()
                hasher.update(initial_bytes)

                # Decode sample for rule headers
                try:
                    sample_text = initial_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    sample_text = initial_bytes.decode("latin-1", errors="replace")

                content_sample = sample_text[:4096]

                # Stream remaining content in 64KB chunks to keep memory usage O(1)
                chunk_size = 65536
                remaining_bytes_count = 0
                newline_count = initial_bytes.count(b"\n")
                collected_chunks = [initial_bytes] if size_bytes <= self.max_file_size else []

                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    hasher.update(chunk)
                    remaining_bytes_count += len(chunk)
                    newline_count += chunk.count(b"\n")
                    if size_bytes <= self.max_file_size:
                        collected_chunks.append(chunk)

                content_hash = hasher.hexdigest()

        except OSError as e:
            return (
                FileInfo(
                    path=file_path,
                    relative_path=rel_path,
                    extension=ext,
                    size_bytes=size_bytes,
                    is_unreadable=True,
                    is_symlink=is_symlink,
                    error_message=str(e),
                ),
                "",
            )

        # For files under max_file_size, decode full text for exact char/line counts
        if size_bytes <= self.max_file_size:
            full_bytes = b"".join(collected_chunks)
            try:
                text = full_bytes.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    text = full_bytes.decode("latin-1")
                except UnicodeDecodeError as e:
                    return (
                        FileInfo(
                            path=file_path,
                            relative_path=rel_path,
                            extension=ext,
                            size_bytes=size_bytes,
                            is_unreadable=True,
                            is_symlink=is_symlink,
                            error_message=f"Text decoding failed: {e}",
                        ),
                        "",
                    )

            char_count = len(text)
            line_count = len(text.splitlines()) if char_count > 0 else 0
        else:
            # For massive files exceeding threshold, estimate char count from byte size
            char_count = size_bytes
            line_count = newline_count

        return (
            FileInfo(
                path=file_path,
                relative_path=rel_path,
                extension=ext,
                size_bytes=size_bytes,
                char_count=char_count,
                line_count=line_count,
                content_hash=content_hash,
                is_symlink=is_symlink,
            ),
            content_sample,
        )
