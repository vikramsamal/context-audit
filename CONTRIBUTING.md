# Contributing to context-audit

Thank you for your interest in contributing to `context-audit`!

## Principles

1. **Safety First**: The tool must remain strictly read-only and offline. No network requests, telemetry, or file modifications.
2. **Minimal Dependencies**: Zero runtime external dependencies. We use the Python 3.11+ standard library.
3. **Simplicity**: Maintain clear, deterministic logic. Avoid unnecessary complexity or speculative features.
4. **Test Coverage**: All changes must include unit/integration tests with high coverage.

## Local Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/vikramsamal/context-audit.git
   cd context-audit
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Run the test suite:
   ```bash
   pytest
   ```

5. Run linters:
   ```bash
   ruff check .
   ```

## Pull Request Process

1. Create a feature branch (`git checkout -b feature/my-feature`).
2. Implement your changes following existing code style.
3. Ensure all tests pass (`pytest`) and linters pass (`ruff check .`).
4. Commit with descriptive messages.
5. Submit a Pull Request targeting the `main` branch.
