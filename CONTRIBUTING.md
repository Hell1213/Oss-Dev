# Contributing to OSS-Dev

Thank you for your interest in contributing to OSS-Dev — the Open Source Contributor Operating System.

## Quick Start

```bash
git clone <your-fork-url>
cd oss-dev
uv sync --dev
uv run pytest
uv run oss-dev --help
```

## Code Standards

- **Python 3.12+** — f-strings, type hints, modern patterns
- **Ruff** — linting (`uv run ruff check`)
- **Mypy** — type checking (`uv run mypy`)
- **Pytest** — testing (`uv run pytest`)
- **Coverage** — coverage reports (`uv run coverage run -m pytest && coverage report`)

## Pull Request Process

1. Open an issue describing the change
2. Fork the repository
3. Create a feature branch (`fix/issue-{number}` or `feat/issue-{number}`)
4. Make changes following code standards
5. Add tests for new functionality
6. Run all checks: `ruff check`, `mypy`, `pytest`
7. Submit PR with clear description referencing the issue

## Review Process

1. All PRs need at least one maintainer approval
2. PRs must pass all CI checks (lint, typecheck, tests)
3. Changes to `src/oss_dev/core/` require architecture review
4. New dependencies require justification

## Commit Messages

Follow conventional commits:
- `fix(scope): description` — Bug fixes
- `feat(scope): description` — New features
- `docs(scope): description` — Documentation
- `refactor(scope): description` — Code refactoring
- `test(scope): description` — Test changes
- `chore(scope): description` — Maintenance

## Code of Conduct

All contributors must follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Questions?

Check [FAQ.md](FAQ.md) or open a discussion.
