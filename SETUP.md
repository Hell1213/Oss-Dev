# Setup Guide

## Prerequisites

- Python 3.12+
- Git
- GitHub CLI (`gh`) — recommended for OSS features
- Gemini API key (from [Google AI Studio](https://aistudio.google.com/apikey))

## Installation

```bash
# Clone
git clone https://github.com/anomalyco/oss-dev.git
cd oss-dev

# Install with uv (recommended)
uv sync --dev

# Verify
uv run oss-dev --version
uv run pytest
```

## Configuration

### Environment Variables

```bash
# Required for OSS features
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# Required for AI features
export GEMINI_API_KEY=AIzaxxxxxxxxxxxx
```

### Project Config

Create `.oss-dev/config.toml` in your repository:

```toml
[model]
name = "gemini-2.0-flash-exp"
provider = "gemini"

[oss]
enabled = true
default_base_branch = "main"
```

## Quick Start

```bash
# Discover good first issues
uv run oss-dev discover issues --good-first --limit 5

# Work on an issue
uv run oss-dev mentor https://github.com/owner/repo/issues/123

# Check setup
uv run oss-dev doctor
```

## GitHub CLI Setup (Recommended)

```bash
# Install
sudo apt install gh

# Authenticate
gh auth login

# Verify
gh issue list
```

## Troubleshooting

See `oss-dev doctor` for diagnostics.
