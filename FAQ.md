# FAQ

## General

**What is OSS-Dev?**
OSS-Dev is an Open Source Contributor Operating System — a CLI platform that helps developers discover, understand, and contribute to open source projects faster.

**Who is it for?**
First-time contributors, GSSoC participants, GSoC aspirants, students, maintainers, and developer communities.

**Is it free?**
Yes, OSS-Dev is MIT licensed and completely free.

## Setup

**Do I need a Gemini API key?**
Yes, for AI-powered features. Get one at https://aistudio.google.com/apikey

**Do I need GitHub CLI?**
Recommended but not required. You can set `GITHUB_TOKEN` environment variable instead.

**Can I use OpenAI instead of Gemini?**
Experimental — the OpenAI provider is mostly unimplemented (raises `NotImplementedError` for most methods). Set `provider = "openai"` and `API_KEY` env var at your own risk.

## Usage

**How do I find issues to work on?**
`oss-dev discover issues --good-first`

**How do I start contributing?**
`oss-dev mentor https://github.com/owner/repo/issues/123`

**Can I resume interrupted work?**
Yes, `oss-dev mentor --resume` restores your last session.

**Is my token safe?**
Yes. Tokens are loaded from environment variables only, never logged or stored in the repository.

## Development

**How do I install from source?**
See [README.md](README.md) (Setup section)

**How do I write a plugin?**
Plugin interfaces exist but a full plugin development guide is not yet published. See [CONTRIBUTING.md](CONTRIBUTING.md) for now.

**How do I contribute?**
See [CONTRIBUTING.md](CONTRIBUTING.md)

## Troubleshooting

**`oss-dev doctor` says GitHub CLI not found**
Install: `sudo apt install gh && gh auth login`

**Tests fail with import errors**
Run `uv sync --dev` to install dependencies.

**Permission denied when accessing repository**
Check `GITHUB_TOKEN` environment variable.
