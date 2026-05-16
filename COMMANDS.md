# CLI Commands

## Overview

```
oss-dev [OPTIONS] COMMAND [ARGS]...
```

## Global Options

| Option | Description |
|--------|-------------|
| `--version, -V` | Show version |
| `--cwd, -C PATH` | Working directory |
| `--help` | Show help |

## Commands

### `oss-dev discover repos`

Discover open source repositories.

Options:
- `--language, -l TEXT` — Filter by language
- `--good-first-issues, -g` — Only repos with good first issues
- `--limit INTEGER` — Maximum results (default: 10)

### `oss-dev discover issues`

Discover issues to work on.

Options:
- `--repo, -r TEXT` — Repository (owner/name)
- `--good-first, -g` — Good first issues only
- `--label, -l TEXT` — Filter by label
- `--limit INTEGER` — Maximum results (default: 10)

### `oss-dev issues list REPO`

List issues for a repository.

Arguments:
- `REPO` — Repository (owner/name)

Options:
- `--state, -s TEXT` — Issue state: open, closed, all
- `--label, -l TEXT` — Filter by label
- `--limit INTEGER` — Maximum results (default: 10)

### `oss-dev issues show REPO ISSUE_NUMBER`

Show details for a specific issue.

Arguments:
- `REPO` — Repository (owner/name)
- `ISSUE_NUMBER` — Issue number

### `oss-dev analyze TARGET`

Analyze a repository or issue.

Arguments:
- `TARGET` — Repository path or URL

Options:
- `--output, -o FILE` — Output file for results

### `oss-dev explain PATH`

Explain code structure and purpose.

Arguments:
- `PATH` — Path to file or directory

Options:
- `--depth, -d INTEGER` — Explanation depth (default: 2)

### `oss-dev roadmap`

Show contribution roadmap for a repository.

Options:
- `--repo, -r TEXT` — Repository (owner/name)

### `oss-dev mentor ISSUE_URL`

Get step-by-step mentoring through a contribution.

Arguments:
- `ISSUE_URL` — GitHub issue URL

Options:
- `--resume, -r` — Resume from checkpoint

### `oss-dev docs [QUERY]`

Search project documentation.

Arguments:
- `QUERY` — Search query (optional)

Options:
- `--repo, -r TEXT` — Repository (owner/name)

### `oss-dev doctor`

Run system diagnostics.

### `oss-dev plugins [ACTION] [NAME]`

Manage plugins.

Arguments:
- `ACTION` — list, install, remove, info (default: list)
- `NAME` — Plugin name

### `oss-dev config [KEY] [VALUE]`

View or modify configuration.

Arguments:
- `KEY` — Config key
- `VALUE` — Config value

Options:
- `--all, -a` — Show all config

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error |
| 2 | CLI usage error |
