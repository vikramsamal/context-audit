"""Command Line Interface for context-audit."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from context_audit import __version__
from context_audit.analyzer import AuditAnalyzer
from context_audit.reporter import JsonReporter, TerminalReporter
from context_audit.tokenizer import DEFAULT_CHARS_PER_TOKEN


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="context-audit",
        description=(
            "Audit your codebase for AI coding context — "
            "local, read-only, and model-agnostic."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  context-audit .
  context-audit /path/to/project
  context-audit . --top 20
  context-audit . --json
  context-audit . --no-color
        """,
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to project directory or file (default: current directory).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output audit results as machine-readable JSON.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        metavar="N",
        help="Number of top context-heavy files to display (default: 10).",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colored output in terminal.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="scan_all",
        help="Include default-ignored directories (e.g. node_modules, dist, .venv).",
    )
    parser.add_argument(
        "--chars-per-token",
        type=float,
        default=DEFAULT_CHARS_PER_TOKEN,
        metavar="N",
        help=f"Estimated characters per token ratio (default: {DEFAULT_CHARS_PER_TOKEN}).",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"context-audit {__version__}",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entry point.

    Args:
        argv: Optional command line arguments list (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, 1 for error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        analyzer = AuditAnalyzer(
            project_path=args.path,
            chars_per_token=args.chars_per_token,
            respect_gitignore=not args.scan_all,
            skip_default_ignored=not args.scan_all,
        )
        report = analyzer.analyze()
    except FileNotFoundError as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1
    except PermissionError as e:
        sys.stderr.write(f"Permission error: {e}\n")
        return 1
    except KeyboardInterrupt:
        sys.stderr.write("\nScan interrupted by user.\n")
        return 130
    except Exception as e:
        sys.stderr.write(f"Unexpected error: {e}\n")
        return 1

    if args.json_output:
        reporter = JsonReporter()
        print(reporter.render(report))
    else:
        reporter = TerminalReporter(color=not args.no_color, top_n=args.top)
        print(reporter.render(report))

    return 0


if __name__ == "__main__":
    sys.exit(main())
