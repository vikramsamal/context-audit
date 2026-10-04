# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Model & Guarantees

`context-audit` is intentionally designed with minimal attack surface:
- **Read-Only**: The tool never modifies, overwrites, or deletes files on your filesystem.
- **Offline / Local**: The tool never makes network connections, initiates sockets, or sends data to external servers or cloud APIs.
- **Zero Runtime Dependencies**: The tool relies strictly on Python's built-in standard library, eliminating third-party supply-chain vulnerabilities.
- **No Telemetry**: No tracking, usage analytics, or error reporting telemetry is collected.

## Reporting a Vulnerability

If you discover a potential security issue in `context-audit`, please report it by opening a security advisory on GitHub or by contacting the maintainer directly.

Please include:
1. Description of the vulnerability.
2. Steps to reproduce the issue.
3. Potential impact.

We will review and address reported vulnerabilities promptly.
