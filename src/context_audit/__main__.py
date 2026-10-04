"""Executable module entrypoint for python -m context_audit."""

from __future__ import annotations

import sys

from context_audit.cli import main

if __name__ == "__main__":
    sys.exit(main())
