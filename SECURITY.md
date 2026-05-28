# Security Policy

## Reporting a Vulnerability

We take the security of this project seriously. If you discover a security vulnerability, please report it responsibly.

**Please use GitHub's private vulnerability reporting feature:**

👉 [Report a vulnerability](https://github.com/gaburn/ado-dashboard/security/advisories/new)

**Do NOT open a public issue for security vulnerabilities.**

## Response Timeline

- **Acknowledgment:** We will acknowledge receipt of your report within **48 hours**.
- **Assessment:** We will provide an initial assessment of the vulnerability within **7 days**.
- **Resolution:** We will work to resolve confirmed vulnerabilities as quickly as possible and will keep you informed of our progress.

## What Constitutes a Security Issue

The following are examples of issues we consider security vulnerabilities:

- **Injection attacks** (command injection via shell-out to `az` / `pwsh`, path-traversal, etc.)
- **Authentication bypass** or improper handling of Azure DevOps credentials / PATs
- **Authorization flaws** (privilege escalation, insecure direct object references)
- **Data exposure** (leaking PATs, session tokens, work-item content, or user emails into logs / config files / clipboard)
- **Cross-Site Request Forgery (CSRF)** in any HTTP-facing component
- **Server-Side Request Forgery (SSRF)** via configurable URLs
- **Remote Code Execution (RCE)** — including via the investigation launcher / spawned subprocesses
- **Denial of Service (DoS)** vulnerabilities
- **Dependency vulnerabilities** with a known exploit path
- **Cryptographic weaknesses** (weak algorithms, improper key management, plaintext secrets at rest)

The following are generally **not** considered security issues:

- Bugs that do not have a security impact
- Feature requests
- Performance issues without a security implication
- Social engineering attacks

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| Current major | ✅ Yes |
| Older versions | ❌ No |

Only the current major version receives security updates. We recommend always using the latest release.

## Disclosure Policy

We follow a coordinated disclosure process. Once a fix is available, we will:

1. Release a patched version
2. Publish a security advisory on GitHub
3. Credit the reporter (unless they prefer to remain anonymous)

Thank you for helping keep this project and its users safe.
