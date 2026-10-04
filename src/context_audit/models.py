"""Data models for context-audit analysis and reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ContextCategory(StrEnum):
    """Categories for classifying context files."""

    GENERATED = "generated"
    VENDOR = "vendor"
    BUILD_ARTIFACT = "build_artifact"
    LOCKFILE = "lockfile"
    LARGE_DATA = "large_data"
    MINIFIED = "minified"
    LOG_FILE = "log_file"
    LARGE_FILE = "large_file"
    DUPLICATE = "duplicate"
    SOURCE_CODE = "source_code"
    DOCUMENTATION = "documentation"
    CONFIG = "config"
    OTHER = "other"


@dataclass
class RuleMatch:
    """A match against a deterministic context rule."""

    rule_id: str
    category: str
    description: str
    is_unnecessary: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "description": self.description,
            "is_unnecessary": self.is_unnecessary,
        }


@dataclass
class FileInfo:
    """Detailed information about an inspected file."""

    path: str
    relative_path: str
    extension: str
    size_bytes: int = 0
    char_count: int = 0
    line_count: int = 0
    estimated_tokens: int = 0
    is_binary: bool = False
    is_symlink: bool = False
    is_unreadable: bool = False
    error_message: str | None = None
    content_hash: str | None = None
    rule_matches: list[RuleMatch] = field(default_factory=list)
    is_potentially_unnecessary: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "relative_path": self.relative_path,
            "extension": self.extension,
            "size_bytes": self.size_bytes,
            "char_count": self.char_count,
            "line_count": self.line_count,
            "estimated_tokens": self.estimated_tokens,
            "is_binary": self.is_binary,
            "is_symlink": self.is_symlink,
            "is_unreadable": self.is_unreadable,
            "error_message": self.error_message,
            "content_hash": self.content_hash,
            "is_potentially_unnecessary": self.is_potentially_unnecessary,
            "rule_matches": [r.to_dict() for r in self.rule_matches],
        }


@dataclass
class FileTypeSummary:
    """Aggregated metrics for a file extension / type."""

    extension: str
    file_count: int
    total_bytes: int
    total_lines: int
    estimated_tokens: int
    percentage_tokens: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "extension": self.extension,
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "total_lines": self.total_lines,
            "estimated_tokens": self.estimated_tokens,
            "percentage_tokens": round(self.percentage_tokens, 2),
        }


@dataclass
class DuplicateGroup:
    """Group of files with identical content hashes."""

    content_hash: str
    files: list[str]
    size_bytes: int
    estimated_tokens: int
    wasted_tokens: int
    wasted_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "content_hash": self.content_hash,
            "files": self.files,
            "size_bytes": self.size_bytes,
            "estimated_tokens": self.estimated_tokens,
            "wasted_tokens": self.wasted_tokens,
            "wasted_bytes": self.wasted_bytes,
        }


@dataclass
class CategorySummary:
    """Summary of files matching a specific context category."""

    category: str
    label: str
    file_count: int
    estimated_tokens: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "label": self.label,
            "file_count": self.file_count,
            "estimated_tokens": self.estimated_tokens,
        }


@dataclass
class AuditReport:
    """Complete report of a context-audit run."""

    project_path: str
    files_scanned: int
    text_files_count: int
    binary_files_skipped: int
    unreadable_files_count: int
    symlinks_skipped: int
    ignored_files_count: int
    total_text_bytes: int
    total_estimated_tokens: int
    potentially_unnecessary_tokens: int
    potential_useful_tokens: int
    potentially_unnecessary_files_count: int
    top_files_by_tokens: list[FileInfo]
    top_files_by_size: list[FileInfo]
    top_files_by_lines: list[FileInfo]
    file_types: list[FileTypeSummary]
    category_summaries: list[CategorySummary]
    duplicate_groups: list[DuplicateGroup]
    total_duplicate_wasted_tokens: int
    warnings: list[str]
    chars_per_token: float
    scan_duration_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project_path,
            "files_scanned": self.files_scanned,
            "text_files": self.text_files_count,
            "binary_files_skipped": self.binary_files_skipped,
            "unreadable_files_skipped": self.unreadable_files_count,
            "symlinks_skipped": self.symlinks_skipped,
            "ignored_files_count": self.ignored_files_count,
            "total_text_bytes": self.total_text_bytes,
            "estimated_tokens": self.total_estimated_tokens,
            "potentially_unnecessary_tokens": self.potentially_unnecessary_tokens,
            "potential_useful_tokens": self.potential_useful_tokens,
            "potentially_unnecessary_files_count": self.potentially_unnecessary_files_count,
            "chars_per_token_used": self.chars_per_token,
            "scan_duration_ms": round(self.scan_duration_ms, 2),
            "file_types": [ft.to_dict() for ft in self.file_types],
            "largest_files": [f.to_dict() for f in self.top_files_by_tokens],
            "potentially_unnecessary": [
                f.to_dict() for f in self.top_files_by_tokens if f.is_potentially_unnecessary
            ],
            "category_breakdown": [c.to_dict() for c in self.category_summaries],
            "duplicates": [d.to_dict() for d in self.duplicate_groups],
            "total_duplicate_wasted_tokens": self.total_duplicate_wasted_tokens,
            "warnings": self.warnings,
        }
