"""Analyzer module for context-audit.

Coordinates filesystem scanning, token estimation, rule evaluation, duplicate
detection, and aggregation into a comprehensive AuditReport.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict

from context_audit.models import (
    AuditReport,
    CategorySummary,
    ContextCategory,
    DuplicateGroup,
    FileInfo,
    FileTypeSummary,
    RuleMatch,
)
from context_audit.rules import evaluate_rules
from context_audit.scanner import Scanner
from context_audit.tokenizer import DEFAULT_CHARS_PER_TOKEN, estimate_tokens_from_char_count


class AuditAnalyzer:
    """Performs full context audit analysis on a target directory."""

    def __init__(
        self,
        project_path: str,
        chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
        respect_gitignore: bool = True,
        skip_default_ignored: bool = True,
    ):
        self.project_path = os.path.abspath(project_path)
        self.chars_per_token = chars_per_token
        self.respect_gitignore = respect_gitignore
        self.skip_default_ignored = skip_default_ignored

    def analyze(self) -> AuditReport:
        """Run scan and generate the AuditReport.

        Returns:
            Populated AuditReport instance.
        """
        start_time = time.perf_counter()

        scanner = Scanner(
            root_dir=self.project_path,
            respect_gitignore=self.respect_gitignore,
            skip_default_ignored=self.skip_default_ignored,
        )

        files_scanned = 0
        binary_files_skipped = 0
        unreadable_files_count = 0
        symlinks_skipped = 0
        unreadable_files: list[FileInfo] = []
        text_files: list[FileInfo] = []

        # Stream and process files
        for file_info, content_sample in scanner.scan():
            files_scanned += 1

            if file_info.is_binary:
                binary_files_skipped += 1
                continue

            if file_info.is_unreadable:
                unreadable_files_count += 1
                unreadable_files.append(file_info)
                if file_info.is_symlink:
                    symlinks_skipped += 1
                continue

            # Estimate tokens
            file_info.estimated_tokens = estimate_tokens_from_char_count(
                file_info.char_count, self.chars_per_token
            )

            # Evaluate deterministic rules
            matches = evaluate_rules(file_info, content_sample)
            file_info.rule_matches = matches
            file_info.is_potentially_unnecessary = any(m.is_unnecessary for m in matches)

            text_files.append(file_info)

        # Detect duplicates using content hash
        hash_to_files: dict[str, list[FileInfo]] = defaultdict(list)
        for f in text_files:
            if f.content_hash and f.size_bytes > 0:
                hash_to_files[f.content_hash].append(f)

        duplicate_groups: list[DuplicateGroup] = []
        total_duplicate_wasted_tokens = 0

        for chash, flist in hash_to_files.items():
            if len(flist) > 1:
                first_file = flist[0]
                wasted_tokens = first_file.estimated_tokens * (len(flist) - 1)
                wasted_bytes = first_file.size_bytes * (len(flist) - 1)
                total_duplicate_wasted_tokens += wasted_tokens

                duplicate_groups.append(
                    DuplicateGroup(
                        content_hash=chash,
                        files=[f.relative_path for f in flist],
                        size_bytes=first_file.size_bytes,
                        estimated_tokens=first_file.estimated_tokens,
                        wasted_tokens=wasted_tokens,
                        wasted_bytes=wasted_bytes,
                    )
                )

                # Mark duplicate copies as potentially unnecessary
                for dup_file in flist[1:]:
                    if not any(m.rule_id == "RULE_DUPLICATE_COPY" for m in dup_file.rule_matches):
                        dup_file.rule_matches.append(
                            RuleMatch(
                                rule_id="RULE_DUPLICATE_COPY",
                                category=ContextCategory.DUPLICATE,
                                description=f"Duplicate of '{first_file.relative_path}'",
                                is_unnecessary=True,
                            )
                        )
                        dup_file.is_potentially_unnecessary = True

        # Sort duplicate groups by wasted tokens descending
        duplicate_groups.sort(key=lambda d: d.wasted_tokens, reverse=True)

        # Aggregate metrics
        text_files_count = len(text_files)
        total_text_bytes = sum(f.size_bytes for f in text_files)
        total_estimated_tokens = sum(f.estimated_tokens for f in text_files)

        # Sum potentially unnecessary tokens
        potentially_unnecessary_tokens = sum(
            f.estimated_tokens for f in text_files if f.is_potentially_unnecessary
        )
        potential_useful_tokens = max(0, total_estimated_tokens - potentially_unnecessary_tokens)
        potentially_unnecessary_files_count = sum(
            1 for f in text_files if f.is_potentially_unnecessary
        )

        # Ranked files
        top_by_tokens = sorted(text_files, key=lambda f: f.estimated_tokens, reverse=True)
        top_by_size = sorted(text_files, key=lambda f: f.size_bytes, reverse=True)
        top_by_lines = sorted(text_files, key=lambda f: f.line_count, reverse=True)

        # File type breakdown
        ext_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"count": 0, "bytes": 0, "lines": 0, "tokens": 0}
        )
        for f in text_files:
            stat = ext_stats[f.extension]
            stat["count"] += 1
            stat["bytes"] += f.size_bytes
            stat["lines"] += f.line_count
            stat["tokens"] += f.estimated_tokens

        file_types: list[FileTypeSummary] = []
        for ext, stat in ext_stats.items():
            pct = (
                (stat["tokens"] / total_estimated_tokens * 100.0)
                if total_estimated_tokens > 0
                else 0.0
            )
            file_types.append(
                FileTypeSummary(
                    extension=ext,
                    file_count=stat["count"],
                    total_bytes=stat["bytes"],
                    total_lines=stat["lines"],
                    estimated_tokens=stat["tokens"],
                    percentage_tokens=pct,
                )
            )
        file_types.sort(key=lambda ft: ft.estimated_tokens, reverse=True)

        # Category summaries
        category_counts: dict[str, dict[str, int]] = defaultdict(
            lambda: {"count": 0, "tokens": 0}
        )
        for f in text_files:
            for match in f.rule_matches:
                category_counts[match.category]["count"] += 1
                category_counts[match.category]["tokens"] += f.estimated_tokens

        cat_labels = {
            ContextCategory.GENERATED: "Generated files",
            ContextCategory.VENDOR: "Vendor / dependency files",
            ContextCategory.BUILD_ARTIFACT: "Build / cache / output files",
            ContextCategory.LOCKFILE: "Dependency lockfiles",
            ContextCategory.LARGE_DATA: "Large data / snapshot files",
            ContextCategory.MINIFIED: "Minified assets",
            ContextCategory.LOG_FILE: "Log files",
            ContextCategory.LARGE_FILE: "High-token files (>20k tokens)",
            ContextCategory.DUPLICATE: "Duplicate files",
        }

        category_summaries: list[CategorySummary] = []
        for cat, label in cat_labels.items():
            if cat in category_counts and category_counts[cat]["count"] > 0:
                category_summaries.append(
                    CategorySummary(
                        category=cat,
                        label=label,
                        file_count=category_counts[cat]["count"],
                        estimated_tokens=category_counts[cat]["tokens"],
                    )
                )

        # Build user-facing warnings summary
        warnings: list[str] = []
        for cat_sum in category_summaries:
            warnings.append(
                f"{cat_sum.file_count} {cat_sum.label.lower()} "
                f"(~{cat_sum.estimated_tokens:,} tokens)"
            )
        if duplicate_groups:
            warnings.append(
                f"{len(duplicate_groups)} duplicate file sets "
                f"(~{total_duplicate_wasted_tokens:,} duplicate tokens)"
            )

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        return AuditReport(
            project_path=self.project_path,
            files_scanned=files_scanned,
            text_files_count=text_files_count,
            binary_files_skipped=binary_files_skipped,
            unreadable_files_count=unreadable_files_count,
            symlinks_skipped=symlinks_skipped,
            ignored_files_count=0,
            total_text_bytes=total_text_bytes,
            total_estimated_tokens=total_estimated_tokens,
            potentially_unnecessary_tokens=potentially_unnecessary_tokens,
            potential_useful_tokens=potential_useful_tokens,
            potentially_unnecessary_files_count=potentially_unnecessary_files_count,
            top_files_by_tokens=top_by_tokens,
            top_files_by_size=top_by_size,
            top_files_by_lines=top_by_lines,
            file_types=file_types,
            category_summaries=category_summaries,
            duplicate_groups=duplicate_groups,
            total_duplicate_wasted_tokens=total_duplicate_wasted_tokens,
            warnings=warnings,
            chars_per_token=self.chars_per_token,
            scan_duration_ms=duration_ms,
            unreadable_files=unreadable_files,
        )
