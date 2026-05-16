# Maintainers Guide

## Current Maintainers

- [Your Name](https://github.com/yourusername) — Project Lead

## Responsibilities

- Reviewing PRs within 48 hours
- Triaging issues weekly
- Releasing versions monthly
- Maintaining CI/CD pipelines
- Enforcing code standards
- Onboarding new contributors
- Managing security disclosures

## Review Process

1. All PRs need at least one maintainer approval
2. PRs must pass all CI checks (lint, typecheck, tests)
3. Changes to `src/oss_dev/core/` require architecture review
4. New dependencies require justification

## Release Process

```bash
# 1. Update version in _version.py
# 2. Update CHANGELOG.md
# 3. Commit: "chore(release): vX.Y.Z"
# 4. Tag: git tag vX.Y.Z
# 5. Push: git push && git push --tags
# 6. GitHub Actions builds and publishes
```

## Community Management

- Label issues within 24 hours
- Respond to questions within 48 hours
- Mark good first issues for newcomers
- Assign mentors for GSSoC contributors

## Security

See [SECURITY.md](SECURITY.md) for the disclosure process.
