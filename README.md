# OSS-Dev

> **Open Source Contributor Operating System**
>
> Discover, understand, and contribute to open source — faster.

[![CI](https://github.com/anomalyco/oss-dev/actions/workflows/ci.yml/badge.svg)](https://github.com/anomalyco/oss-dev/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue)](https://python.org)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## Quick Start

```bash
# Install
uv sync --dev

# Discover issues to work on
uv run oss-dev discover issues --good-first

# Get mentoring through a contribution
uv run oss-dev mentor https://github.com/owner/repo/issues/123
```

## What is OSS-Dev?

OSS-Dev helps developers contribute to open source by automating workflow mechanics while preserving quality standards.

### For Contributors

- **Discover** — Find projects and issues matching your skills
- **Mentor** — Step-by-step guidance through your first contributions
- **Automate** — Branching, commits, PRs handled for you
- **Learn** — Understand codebases through intelligent analysis

### For Maintainers

- **Quality** — Contributions arrive in consistent, reviewable format
- **Scale** — Process more issues without sacrificing standards
- **Onboard** — Automatic contributor guidance reduces questions

## Installation

See [SETUP.md](SETUP.md) for detailed setup instructions.

**Prerequisites:**
- Python 3.12+
- Git
- GitHub CLI (recommended) or `GITHUB_TOKEN`
- Gemini API key

## Commands

| Command | Description |
|---------|-------------|
| `oss-dev discover repos` | Find projects to contribute to |
| `oss-dev discover issues` | Find issues to work on |
| `oss-dev issues list <repo>` | List repository issues |
| `oss-dev issues show <repo> <num>` | Show issue details |
| `oss-dev analyze <target>` | Analyze a repository |
| `oss-dev explain <path>` | Explain code structure |
| `oss-dev roadmap` | Show contribution roadmap |
| `oss-dev mentor <issue-url>` | Guided contribution workflow |
| `oss-dev docs [query]` | Search documentation |
| `oss-dev doctor` | Run diagnostics |
| `oss-dev plugins` | Manage plugins |
| `oss-dev config` | Manage configuration |

See [COMMANDS.md](COMMANDS.md) for full documentation.

## Architecture

```
CLI Layer → Service Layer → Core Layer → Provider Layer
               ↓                ↓              ↓
         Intelligence      Contracts      GitHub/Git/LLM
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the complete blueprint.

## Project Status

**Current Version:** 0.2.0 — Architecture Redesign

See [ROADMAP.md](ROADMAP.md) for planned features and [CHANGELOG.md](CHANGELOG.md) for release history.

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

- First time? Look for [good first issues](https://github.com/anomalyco/oss-dev/labels/good%20first%20issue)
- Check [FAQ.md](FAQ.md) for common questions
- Review our [Code of Conduct](CODE_OF_CONDUCT.md)

## Documentation

| Document | Purpose |
|----------|---------|
| [SETUP.md](SETUP.md) | Development environment setup |
| [COMMANDS.md](COMMANDS.md) | CLI command reference |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Architecture blueprint |
| [PLUGIN_DEVELOPMENT.md](PLUGIN_DEVELOPMENT.md) | Plugin development guide |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |
| [ROADMAP.md](ROADMAP.md) | Feature roadmap |
| [VISION.md](VISION.md) | Project vision |
| [FAQ.md](FAQ.md) | Frequently asked questions |
| [SECURITY.md](SECURITY.md) | Security policy |
| [MAINTAINERS.md](MAINTAINERS.md) | Maintainer guide |
| [CHANGELOG.md](CHANGELOG.md) | Release history |

## License

MIT — see [LICENSE](LICENSE)
