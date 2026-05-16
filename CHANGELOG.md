# Changelog

## [0.2.0] — 2026-05-16

### Added
- New `src/oss_dev/` package structure
- Typer-based CLI with professional UX
- Rich-themed UI components (console, themes, displays)
- Core contracts (workflow, provider, plugin interfaces)
- Deterministic workflow state machine
- File-based state persistence
- Async approval manager with confirmation protocol
- GitHub provider (gh CLI implementation)
- Git provider abstraction
- Configuration models and loader
- Error hierarchy with typed exceptions
- Comprehensive governance docs:
  - ARCHITECTURE.md, CONTRIBUTING.md, ROADMAP.md
  - SECURITY.md, CODE_OF_CONDUCT.md, SETUP.md
  - COMMANDS.md, PLUGIN_DEVELOPMENT.md
  - MAINTAINERS.md, CHANGELOG.md, VISION.md, FAQ.md

### Changed
- Moved from Click-only to Typer primary CLI framework
- Version bumped to 0.2.0

### Removed
- Placeholder `NotImplementedError` patterns in providers
- Broken synchronous approval callback pattern

## [0.1.0] — Initial Hackathon Release

- Click-based CLI
- OSS workflow with 7 phases
- GitHub integration via gh CLI
- Branch memory system
- Agent event streaming
- Basic approval system
