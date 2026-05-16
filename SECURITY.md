# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | yes       |
| < 0.2   | no        |

## Reporting a Vulnerability

OSS-Dev handles credentials and API tokens. If you discover a security vulnerability:

1. **Do NOT** open a public GitHub issue
2. Email the maintainers directly or open a [security advisory](https://github.com/anomalyco/oss-dev/security/advisories)
3. Include a detailed description and reproduction steps

You should receive a response within 48 hours. If not, follow up.

## Scope

- Credential exposure in logs or output
- Injection vulnerabilities in shell commands
- Unsafe token storage
- Approval bypass
- Provider credential leakage

## Out of Scope

- Dependency CVEs with known fixes
- Phishing attacks against maintainers
- DOS attacks

## Security Measures

- All credentials loaded from environment variables only
- `.oss-dev/` directory is gitignored (contains workflow state)
- Approval system blocks dangerous commands by default
- `git` subprocess commands are parameterized (no shell injection)
- No hardcoded secrets in codebase
- Automated secret scanning via Gitleaks in CI

## Disclosure Process

1. Report received and acknowledged
2. Investigation and fix development
3. Fix released in next patch version
4. Public disclosure after 30 days
