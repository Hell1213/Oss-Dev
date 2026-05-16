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
# Clone and install
git clone https://github.com/anomalyco/oss-dev.git
cd oss-dev
uv sync --dev

# Set credentials
export GITHUB_TOKEN=your_github_token
export GEMINI_API_KEY=your_gemini_api_key

# Verify
uv run oss-dev --version
uv run pytest
```

## Vision

Open source contribution is needlessly hard. New contributors face unclear starting points, complex workflow mechanics, and overwhelming codebases. OSS-Dev is a CLI platform that:

1. **Discovers** — Find projects and issues matching your skills
2. **Guides** — Step-by-step mentoring through contributions
3. **Automates** — Mechanical workflow (branching, commits, PRs)
4. **Analyzes** — Repository intelligence for contribution readiness
5. **Connects** — Community features and mentoring

**Target users:** First-time contributors, GSSoC/GSoC participants, students, maintainers, and developer communities.

**Design principles:** Contributor-first, deterministic behavior, safety gates, extensibility, professional CLI experience.

## Installation

### Prerequisites

- Python 3.12+
- Git
- GitHub CLI (`gh`) — recommended for OSS features
- Gemini API key (from [Google AI Studio](https://aistudio.google.com/apikey))

### Setup

```bash
# Clone and install
git clone https://github.com/anomalyco/oss-dev.git
cd oss-dev
uv sync --dev

# Verify
uv run oss-dev --version
uv run pytest
```

### Configuration

Set environment variables:

```bash
export GITHUB_TOKEN=your_github_token
export GEMINI_API_KEY=your_gemini_api_key
```

Optional project config (`.oss-dev/config.toml`):

```toml
[model]
name = "gemini-2.0-flash-exp"
provider = "gemini"

[oss]
enabled = true
default_base_branch = "main"
```

### GitHub CLI Setup (Optional but Recommended)

```bash
sudo apt install gh
gh auth login
```

### Troubleshooting

Run `uv run oss-dev doctor` for system diagnostics.

## Commands

### Global Options

| Option | Description |
|--------|-------------|
| `--version, -V` | Show version |
| `--cwd, -C PATH` | Working directory |
| `--help` | Show help |

### Command Reference

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
| `oss-dev config` | Manage configuration |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error |
| 2 | CLI usage error |

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

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) to get started. Look for [good first issues](https://github.com/anomalyco/oss-dev/labels/good%20first%20issue) to find starter tasks.

Questions? Check [FAQ.md](FAQ.md) or open a discussion.

## License

MIT — see [LICENSE](LICENSE)
