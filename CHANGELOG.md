# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-04

### Added
- Initial release of `context-audit`.
- Safe recursive filesystem scanner with symlink cycle protection and `.git` ignore.
- Hierarchical `.gitignore` parsing and pattern matching.
- Deterministic rule detection for generated code, vendor directories, build artifacts, lockfiles, minified files, test snapshots, and large data files.
- SHA-256 content-hash duplicate file detection with redundant token calculations.
- Model-agnostic token estimation (~4.0 chars/token configurable ratio).
- Rich terminal reporter with ANSI styling, file type breakdowns, and issue summaries.
- Machine-readable JSON output via `--json` flag.
- Zero external runtime dependencies (100% Python standard library).
- Comprehensive test suite covering safety, unreadable files, encoding fallbacks, and integration scenarios.
