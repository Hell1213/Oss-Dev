# OSS-Dev Roadmap

## Phase 1 — Stabilization (Complete)

- [x] pyproject.toml with uv
- [x] CI/CD workflows
- [x] Secret scanning
- [x] Test fixes
- [x] Lint cleanup
- [x] Working CLI

## Phase 2 — Architecture Redesign (Complete)

- [x] Architecture blueprint (ARCHITECTURE.md)
- [x] Module ownership defined
- [x] Provider contracts designed
- [x] Plugin contracts designed
- [x] Approval architecture redesigned
- [x] Migration strategy documented

## Phase 3 — Foundation Restructuring (In Progress)

- [x] src/oss_dev/ package scaffold
- [x] Core contracts and interfaces
- [x] Config models and loader
- [x] Workflow state machine
- [x] State persistence
- [x] Approval manager
- [x] GitHub provider implementation
- [x] Git provider implementation
- [ ] Legacy code migration
- [ ] Old package removal

## Phase 4 — CLI Platform (In Progress)

- [x] Typer CLI app scaffold
- [x] Rich theme definitions
- [x] Display helpers
- [ ] Command implementations (discover, issues, analyze, explain, roadmap, mentor, docs, doctor, plugins, config)
- [ ] Consistent error handling across all commands
- [ ] JSON output mode
- [ ] Tab completion

## Phase 5 — Testing Hardening

- [ ] Unit tests for workflow state machine
- [ ] Unit tests for approval manager
- [ ] Unit tests for state persistence
- [ ] Unit tests for config loader
- [ ] Unit tests for GitHub provider
- [ ] Unit tests for Git provider
- [ ] Integration tests for CLI commands
- [ ] End-to-end contribution flow test
- [ ] Coverage > 80%

## Phase 6 — OSS Governance

- [x] ARCHITECTURE.md
- [x] CONTRIBUTING.md
- [x] ROADMAP.md
- [x] SECURITY.md
- [x] CODE_OF_CONDUCT.md
- [x] SETUP.md
- [x] COMMANDS.md
- [x] PLUGIN_DEVELOPMENT.md
- [x] MAINTAINERS.md
- [x] CHANGELOG.md
- [x] VISION.md
- [x] FAQ.md
- [x] Issue templates
- [x] PR template
- [x] GitHub labels

## Phase 7 — Provider Expansion

- [ ] LLM provider implementation (Gemini)
- [ ] LLM provider implementation (OpenAI fallback)
- [ ] Provider registry with auto-detection
- [ ] Caching layer for API calls

## Phase 8 — Intelligence Layer

- [ ] Repository stack detection
- [ ] Documentation intelligence
- [ ] Issue classification
- [ ] Dependency graph analysis
- [ ] Contribution guidance

## Phase 9 — Plugin Ecosystem

- [ ] Plugin loader with entry points
- [ ] Plugin registry
- [ ] Built-in plugins
- [ ] Plugin development guide
- [ ] Plugin marketplace support

## Phase 10 — GSSoC Readiness

- [ ] Good first issues labeled
- [ ] Mentor assignment workflow
- [ ] Contributor onboarding under 10 minutes
- [ ] Demo scripts
- [ ] Release automation
- [ ] Submission package

## Future

- GitHub Actions plugin
- GitLab provider
- Terminal UI (Textual)
- Web dashboard
- Analytics dashboard
- VS Code extension
