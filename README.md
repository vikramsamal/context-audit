# context-audit

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Dependencies: 0](https://img.shields.io/badge/dependencies-0-success.svg)](pyproject.toml)
[![Read Only](https://img.shields.io/badge/mode-read--only-green.svg)](SECURITY.md)

**Understand your project's AI context before your coding agent does.**

`context-audit` is a fast, local, read-only CLI that analyzes a software project and identifies files, directories, and data that may create unnecessary or bloated AI coding context.

No API key. No cloud. No LLM. No files modified. 100% offline.

```bash
context-audit .
```

---

## The Problem

When you work with AI coding agents (Cursor, Claude Code, GitHub Copilot, VS Code AI, Ollama, OpenAI/Gemini coding tools, MCP servers), agents index or ingest large portions of your codebase into their prompt context windows.

However, modern repositories are filled with files that dilute context, waste token budgets, and degrade reasoning performance:
- Auto-generated protobuf, gRPC, and OpenAPI client stubs
- Minified JavaScript and CSS bundles
- Massive dependency lockfiles (`package-lock.json`, `poetry.lock`, `Cargo.lock`)
- Large JSON/XML fixtures and database dumps
- Duplicate configuration and backup files
- Build artifacts and test snapshots

`context-audit` gives developers instant visibility into their repository's AI context footprint before feeding it to an agent.

---

## Key Features

- **⚡ Zero external dependencies**: Built entirely on standard Python 3.11+ library for instant execution and zero supply-chain risk.
- **🔒 100% Read-Only & Offline**: Never modifies, deletes, or writes files. Never initiates network connections. Zero telemetry.
- **📊 Token Estimation**: Model-agnostic byte-pair encoding approximation (~4 characters per token).
- **🎯 Deterministic Categorization**: Accurately flags generated code, vendor directories, lockfiles, minified files, test snapshots, and large data files.
- **🔍 Content Hash Duplicate Detection**: Identifies exact duplicate files using SHA-256 and computes duplicate wasted tokens.
- **📁 Git & .gitignore Aware**: Respects hierarchical `.gitignore` rules and ignores `.git` internals.
- **🤖 Machine-Readable JSON**: Supports `--json` flag for CI/CD checks, automation, and tooling.

---

## Installation

### From GitHub
```bash
pip install git+https://github.com/vikramsamal/context-audit.git
```

### Using `pipx` (Recommended for global CLI)
```bash
pipx install context-audit
```

### Using `pip`
```bash
pip install context-audit
```

### Local Development Mode
```bash
git clone https://github.com/vikramsamal/context-audit.git
cd context-audit
pip install -e .
```

---

## Usage

### Basic Audit
Run in the current directory:
```bash
context-audit .
```

### Audit a Specific Path
```bash
context-audit /path/to/project
```

### Show Top 20 Context-Heavy Files
```bash
context-audit . --top 20
```

### Machine-Readable JSON Output
```bash
context-audit . --json
```

### Disable ANSI Colors
```bash
context-audit . --no-color
```

### Include Default Ignored Directories
```bash
context-audit . --all
```

---

## Example Output

```text
Context Audit
==============

Project: /Users/username/code/my-app

Files scanned:                  48
Text files:                     42
Binary files skipped:            6

Total text size:         384.20 KB
Estimated tokens:           96,050

Potentially unnecessary:    54,200 tokens
Potential useful context:   41,850 tokens

Context by file type
------------------------------
.ts                 18 files     38,400 tokens ( 40.0%)
.json                8 files     32,100 tokens ( 33.4%)
.py                 10 files     18,250 tokens ( 19.0%)
.md                  6 files      7,300 tokens (  7.6%)

Top context-heavy files
------------------------------
   28,400  package-lock.json [unnecessary]
   14,200  src/generated/api_client.ts [unnecessary]
    8,200  docs/architecture.md
    6,400  src/server.ts
    4,100  tests/fixtures/mock_data.json [unnecessary]

Potential context issues
------------------------------
⚠ 1 dependency lockfiles (~28,400 tokens)
⚠ 1 generated files (~14,200 tokens)
⚠ 1 large data / snapshot files (~4,100 tokens)
⚠ 1 duplicate file sets (~7,500 duplicate tokens)

Potential duplicate files
------------------------------
Duplicate content (2 copies, 7,500 redundant tokens):
  • config/defaults.json
  • backup/config_backup.json

Suggested next step
------------------------------
Review the flagged files before allowing an AI coding
agent to index or include them in context.

No files were modified.
No data was uploaded.
```

---

## JSON Output Schema

When invoked with `--json`, `context-audit` outputs structured JSON suitable for scripting:

```json
{
  "project": "/path/to/project",
  "files_scanned": 48,
  "text_files": 42,
  "binary_files_skipped": 6,
  "unreadable_files_skipped": 0,
  "symlinks_skipped": 0,
  "ignored_files_count": 0,
  "total_text_bytes": 393420,
  "estimated_tokens": 96050,
  "potentially_unnecessary_tokens": 54200,
  "potential_useful_tokens": 41850,
  "potentially_unnecessary_files_count": 4,
  "chars_per_token_used": 4.0,
  "scan_duration_ms": 14.8,
  "file_types": [
    {
      "extension": ".ts",
      "file_count": 18,
      "total_bytes": 153600,
      "total_lines": 3420,
      "estimated_tokens": 38400,
      "percentage_tokens": 40.0
    }
  ],
  "largest_files": [],
  "potentially_unnecessary": [],
  "category_breakdown": [],
  "duplicates": [],
  "total_duplicate_wasted_tokens": 7500,
  "warnings": []
}
```

---

## Detection Rules Reference

`context-audit` uses deterministic rules to classify files into context categories:

| Category | Examples & Detection Criteria |
| :--- | :--- |
| **Generated Code** | Headers (`@generated`, `Code generated by`, `DO NOT EDIT`), filenames (`*.pb.go`, `*_pb2.py`, `*.g.dart`, `*.min.js`, `*.map`). |
| **Vendor Dependencies** | Directories like `node_modules/`, `vendor/`, `Pods/`, `bower_components/`, `.venv/`. |
| **Build Artifacts** | Directories like `dist/`, `build/`, `target/`, `.next/`, `coverage/`, `.cache/`. |
| **Lockfiles** | `package-lock.json`, `poetry.lock`, `Cargo.lock`, `pnpm-lock.yaml`, `go.sum`, `Gemfile.lock`. |
| **Large Data / Snapshots** | Data files (`.json`, `.xml`, `.csv`, `.sql`, `.dump`) exceeding 50 KB or test snapshots (`__snapshots__/`, `*.snap`). |
| **Minified Assets** | `.min.js`, `.min.css`, or files with average line lengths exceeding 250 characters. |
| **Duplicate Files** | SHA-256 hash matching identifying duplicate copies and redundant context tokens. |

---

## Safety Guarantees

`context-audit` is designed with strict security principles:
- **Local only**: All operations run locally on your device.
- **Read-only**: Never modifies, renames, writes, or deletes any files in your workspace.
- **No network calls**: Makes zero outbound HTTP/socket calls.
- **No telemetry / analytics**: Zero tracking or user data collection.
- **No LLM / API keys required**: Completely deterministic rules engine.

---

## Limitations

- **Estimated Token Counts**: Token counts are heuristic estimates based on character count ratios (~4 chars/token). Real token counts vary slightly across tokenizer implementations (cl100k, Llama, Claude, etc.).
- **Deterministic Heuristics**: File classification uses standard naming conventions and header markers. Some proprietary or custom generated formats might not match default rules.

---

## Roadmap

The following capabilities are planned for future releases based on user feedback:
- [ ] `.aiignore` file generation
- [ ] Cursor `.cursorrules` and VS Code context exclusions exporter
- [ ] Tokenizer-specific exact counting options (tiktoken / tokenizers)
- [ ] Context budget and diff comparisons between git branches

---

## License

MIT License. See [LICENSE](LICENSE) for details.
