# Security Policy

## Supported Versions

Only the latest commit on the `main` branch receives security fixes. This project has no versioned releases at this time.

## Scope

Musical Markdown is a plain-text format toolchain — a validator, formatter, and set of exporters. It processes `.mmd` files you provide and does not accept network input, manage authentication, or handle credentials. Security-relevant concerns are limited to:

- **File parsing**: malformed or adversarially crafted `.mmd` files causing unexpected behavior (crashes, excessive resource use)
- **mmd_player.html**: the browser-based player executes JavaScript locally; any XSS-style injection in score metadata would be in scope

## Reporting a Vulnerability

Please **do not open a public GitHub issue** for security vulnerabilities.

Report privately by emailing **km.vibecoder@gmail.com** with:
- A description of the vulnerability and its potential impact
- Steps to reproduce (a minimal `.mmd` file or browser payload that triggers the issue)
- Any suggested fix, if you have one

You can expect an acknowledgment within **72 hours** and a resolution or status update within **14 days**.
