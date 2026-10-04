"""Reporters for context-audit (Terminal and JSON)."""

from __future__ import annotations

import json
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context_audit.models import AuditReport


def format_bytes(num_bytes: int) -> str:
    """Format bytes into a human-readable string (B, KB, MB, GB)."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.2f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


class Colors:
    """ANSI terminal styling codes."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"

    @classmethod
    def disable(cls) -> None:
        """Disable all color codes."""
        cls.RESET = ""
        cls.BOLD = ""
        cls.DIM = ""
        cls.CYAN = ""
        cls.GREEN = ""
        cls.YELLOW = ""
        cls.RED = ""
        cls.BLUE = ""
        cls.MAGENTA = ""


class TerminalReporter:
    """Renders clean, human-readable terminal reports."""

    def __init__(self, color: bool = True, top_n: int = 10):
        # Respect NO_COLOR env var or explicit disable
        if not color or os.environ.get("NO_COLOR") or not sys.stdout.isatty():
            Colors.disable()
        self.top_n = top_n

    def render(self, report: AuditReport) -> str:
        """Generate terminal report string from an AuditReport."""
        lines: list[str] = []

        # Title banner
        lines.append(f"{Colors.BOLD}{Colors.CYAN}Context Audit{Colors.RESET}")
        lines.append(f"{Colors.CYAN}{'=' * 30}{Colors.RESET}")
        lines.append("")
        lines.append(f"{Colors.BOLD}Project:{Colors.RESET} {report.project_path}")
        lines.append("")

        # Scan Overview
        lines.append(f"Files scanned:             {report.files_scanned:>8,}")
        lines.append(f"Text files:                {report.text_files_count:>8,}")
        if report.binary_files_skipped > 0:
            lines.append(f"Binary files skipped:      {report.binary_files_skipped:>8,}")
        if report.unreadable_files_count > 0:
            lines.append(f"Unreadable files skipped:  {report.unreadable_files_count:>8,}")
        lines.append("")

        # Context Token Overview
        lines.append(f"Total text size:          {format_bytes(report.total_text_bytes):>10}")
        est_tokens_str = f"{report.total_estimated_tokens:>10,}"
        lines.append(f"{Colors.BOLD}Estimated tokens:         {est_tokens_str}{Colors.RESET}")
        lines.append("")

        unnecessary_color = Colors.YELLOW if report.potentially_unnecessary_tokens > 0 else ""
        unnec_str = f"{report.potentially_unnecessary_tokens:>10,} tokens"
        lines.append(
            f"{unnecessary_color}Potentially unnecessary:  {unnec_str}{Colors.RESET}"
        )
        useful_str = f"{report.potential_useful_tokens:>10,} tokens"
        lines.append(f"{Colors.GREEN}Potential useful context: {useful_str}{Colors.RESET}")
        lines.append("")

        # File Types Breakdown (Top 6)
        if report.file_types:
            lines.append(f"{Colors.BOLD}Context by file type{Colors.RESET}")
            lines.append(f"{'-' * 30}")
            for ft in report.file_types[:6]:
                ext_label = ft.extension if ft.extension != "(no ext)" else "no extension"
                pct_str = f"{ft.percentage_tokens:>5.1f}%"
                ft_tok_str = f"{ft.estimated_tokens:>9,}"
                lines.append(
                    f"{ext_label:<14} {ft.file_count:>4} files  {ft_tok_str} tokens ({pct_str})"
                )
            if len(report.file_types) > 6:
                other_tokens = sum(ft.estimated_tokens for ft in report.file_types[6:])
                other_files = sum(ft.file_count for ft in report.file_types[6:])
                other_pct = (
                    (other_tokens / report.total_estimated_tokens * 100.0)
                    if report.total_estimated_tokens > 0
                    else 0.0
                )
                oth_tok_str = f"{other_tokens:>9,}"
                oth_pct_str = f"{other_pct:>5.1f}%"
                lines.append(
                    f"{'other':<14} {other_files:>4} files  {oth_tok_str} tokens ({oth_pct_str})"
                )
            lines.append("")

        # Top Context-Heavy Files
        top_files = report.top_files_by_tokens[: self.top_n]
        if top_files:
            lines.append(f"{Colors.BOLD}Top context-heavy files{Colors.RESET}")
            lines.append(f"{'-' * 30}")
            for f in top_files:
                flag = (
                    f" {Colors.YELLOW}[unnecessary]{Colors.RESET}"
                    if f.is_potentially_unnecessary
                    else ""
                )
                lines.append(f"{f.estimated_tokens:>9,}  {f.relative_path}{flag}")
            lines.append("")

        # Potential Context Issues
        if report.category_summaries or report.duplicate_groups:
            lines.append(f"{Colors.BOLD}Potential context issues{Colors.RESET}")
            lines.append(f"{'-' * 30}")
            for cat in report.category_summaries:
                lines.append(
                    f"{Colors.YELLOW}⚠{Colors.RESET} {cat.file_count} {cat.label.lower()} "
                    f"(~{cat.estimated_tokens:,} tokens)"
                )
            if report.duplicate_groups:
                dup_count = len(report.duplicate_groups)
                dup_tok = report.total_duplicate_wasted_tokens
                lines.append(
                    f"{Colors.YELLOW}⚠{Colors.RESET} {dup_count} duplicate file sets "
                    f"(~{dup_tok:,} duplicate tokens)"
                )
            lines.append("")

        # Duplicate Files Detail
        if report.duplicate_groups:
            lines.append(f"{Colors.BOLD}Potential duplicate files{Colors.RESET}")
            lines.append(f"{'-' * 30}")
            for d in report.duplicate_groups[:5]:
                copies_cnt = len(d.files)
                wasted_str = f"{d.wasted_tokens:,} redundant tokens"
                lines.append(f"Duplicate content ({copies_cnt} copies, {wasted_str}):")
                for path in d.files:
                    lines.append(f"  • {path}")
                lines.append("")
            if len(report.duplicate_groups) > 5:
                lines.append(f"... and {len(report.duplicate_groups) - 5} more duplicate sets.")
                lines.append("")

        # Unreadable / Skipped Files Detail
        if report.unreadable_files:
            lines.append(f"{Colors.BOLD}Unreadable / Skipped files{Colors.RESET}")
            lines.append(f"{'-' * 30}")
            for uf in report.unreadable_files[:5]:
                err_desc = uf.error_message or "Unreadable file"
                lines.append(f"  • {uf.relative_path}: {err_desc}")
            if len(report.unreadable_files) > 5:
                rem = len(report.unreadable_files) - 5
                lines.append(f"  ... and {rem} more unreadable files.")
            lines.append("")

        # Suggested Next Steps
        lines.append(f"{Colors.BOLD}Suggested next step{Colors.RESET}")
        lines.append(f"{'-' * 30}")
        lines.append("Review the flagged files before allowing an AI coding")
        lines.append("agent to index or include them in context.")
        lines.append("")
        lines.append(f"{Colors.DIM}No files were modified.{Colors.RESET}")
        lines.append(f"{Colors.DIM}No data was uploaded.{Colors.RESET}")
        lines.append("")

        return "\n".join(lines)


class JsonReporter:
    """Renders machine-readable JSON output."""

    def __init__(self, indent: int = 2):
        self.indent = indent

    def render(self, report: AuditReport) -> str:
        """Serialize AuditReport to formatted JSON string."""
        return json.dumps(report.to_dict(), indent=self.indent)
