"""context-audit: Local, read-only AI coding context analyzer."""

from __future__ import annotations

from context_audit.analyzer import AuditAnalyzer
from context_audit.models import AuditReport, FileInfo, RuleMatch
from context_audit.scanner import Scanner
from context_audit.tokenizer import estimate_tokens

__version__ = "0.1.0"
__all__ = [
    "__version__",
    "AuditAnalyzer",
    "AuditReport",
    "FileInfo",
    "RuleMatch",
    "Scanner",
    "estimate_tokens",
]
