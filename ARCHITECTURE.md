# OSS-Dev Architecture

> Open Source Contributor Operating System — Architecture Blueprint

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Current Architecture Analysis](#2-current-architecture-analysis)
3. [Target Architecture](#3-target-architecture)
4. [Module Ownership](#4-module-ownership)
5. [Dependency Graph](#5-dependency-graph)
6. [Workflow State Machine](#6-workflow-state-machine)
7. [Provider Contracts](#7-provider-contracts)
8. [Plugin Contracts](#8-plugin-contracts)
9. [Config Architecture](#9-config-architecture)
10. [Approval Architecture](#10-approval-architecture)
11. [Error Handling Strategy](#11-error-handling-strategy)
12. [Migration Strategy](#12-migration-strategy)

---

## 1. Architecture Overview

OSS-Dev is a **modular monolith** with strict layering:

```
CLI Layer        →  Typer commands, rich output, user interaction only
Service Layer    →  Domain logic (discovery, mentoring, planning, setup)
Core Layer       →  Workflow engine, state machine, orchestration, approvals
Provider Layer   →  GitHub, Git, LLM integrations (isolated behind contracts)
Intelligence     →  Repository analysis, documentation, issue analysis
Plugin Layer     →  Extension points, registry, built-in plugins
Config Layer     →  TOML-based, layered (system > project > env)
```

**Rules:**

- Each layer imports only from itself or layers below
- CLI never contains business logic
- Core never imports CLI, services, or providers directly
- Providers are swappable behind typed contracts
- All mutations require explicit approval
- No hidden side effects
- Deterministic workflow transitions only

---

## 2. Current Architecture Analysis

### 2.1 Strengths (Preserve)

| Asset | Location | Rationale |
|---|---|---|
| Agent event system | `agent/events.py` | Clean observer pattern for CLI/UI |
| Tool base class | `tools/base.py` | Solid abstraction with schema, validation, diff tracking |
| Session management | `agent/session.py` | Proper lifecycle with initialize/shutdown |
| Context management | `context/manager.py` | Working message history with compression |
| Config loading | `config/loader.py` | Layered TOML loading works correctly |
| Repository analysis | `oss/repository.py` | Good detection logic for project types |
| Branch memory | `oss/memory.py` | Valid persistence pattern, worth evolving |
| Approval safety patterns | `safety/approval.py` | Command safety classification is sound |
| Tool implementations | `tools/builtin/` | Well-structured individual tools |
| OSS tools | `tools/oss/` | Individual tool files are reasonable |

### 2.2 Problems (Redesign)

| Problem | Location | Severity | Impact |
|---|---|---|---|
| God module | `oss/workflow.py` (1085 lines) | CRITICAL | Single file does orchestration, validation, prompt generation |
| Split-brain CLI | `main.py` + `cli/oss_commands.py` | CRITICAL | Duplicate CLI orchestration, conflicting UX patterns |
| Hidden workflow state | `oss/workflow.py` + `main.py` CLI class | CRITICAL | State mutated across multiple objects |
| Broken approval callback | `safety/approval.py` + `agent/agent.py` | HIGH | Callback-based async patterns, missing await |
| Weak GitHub provider | `oss/github.py` | HIGH | Tight coupling, `NotImplementedError` placeholders |
| Click-only CLI | `main.py` + `cli/oss_commands.py` | MEDIUM | No Typer, inconsistent UX, poor help text |
| No provider abstractions | Missing | HIGH | GitHub/Git/LLM are not swappable |
| No plugin system | Missing | MEDIUM | No extension points for community |
| Inconsistent test patterns | `tests/` | MEDIUM | Mix of unit and integration without clear strategy |
| No governance docs | Missing | MEDIUM | No CONTRIBUTING, SECURITY, ROADMAP |

### 2.3 Key Architectural Debt

1. **Duplicate CLI orchestration flows** — Three places manage workflow: `main.py` CLI class `_handle_oss_fix`, `cli/oss_commands.py` `oss_fix`, and `oss/workflow.py` `mark_phase_complete`. This is split-brain architecture.

2. **Split-brain workflow state** — `OSSWorkflow` object is created fresh each command in `cli/oss_commands.py`. State is loaded from `BranchMemoryManager` but the workflow object lifecycle is inconsistent.

3. **Hidden workflow instances** — Each CLI command (`oss_fix`, `oss_review`, `oss_resume`, `oss_switch`) creates its own `OSSWorkflow` instance with its own async loop. No shared state machine.

4. **God workflow module** — `oss/workflow.py` contains phase transition logic, validation, prompt generation (7 massive prompt methods), git operations, and state persistence. This must be decomposed.

5. **Weak provider abstractions** — `oss/github.py` has `_fetch_issue_via_api` that raises `NotImplementedError`. No provider registry. No contract/interface.

6. **Broken approval architecture** — `ApprovalManager` has a `confirmation_callback: Callable` that's set externally. The callback is synchronous but used in async context. The `request_confirmation` method returns `True` when no callback is set (dangerous default).

7. **Unsafe mutation patterns** — Multiple places use `subprocess.run` directly with user-derived strings. No sandbox. No path validation for shell commands.

---

## 3. Target Architecture

### 3.1 Package Layout

```
src/oss_dev/
    __init__.py
    _version.py

    cli/
        __init__.py
        app.py                  # Typer app, main entry
        commands/
            __init__.py
            discover.py         # oss-dev discover
            issues.py           # oss-dev issues
            analyze.py          # oss-dev analyze
            explain.py          # oss-dev explain
            roadmap.py          # oss-dev roadmap
            mentor.py           # oss-dev mentor
            docs.py             # oss-dev docs
            doctor.py           # oss-dev doctor
            plugins.py          # oss-dev plugins
            config_cmd.py       # oss-dev config
        ui/
            __init__.py
            console.py          # Rich console singleton
            themes.py           # Theme definitions
            displays.py         # Display helpers (panels, tables)
        prompts/
            __init__.py

    core/
        __init__.py
        workflow/
            __init__.py
            state_machine.py    # Deterministic state transitions
            phases.py           # Phase definitions and validators
            errors.py           # Workflow-specific errors
        orchestration/
            __init__.py
            engine.py           # Workflow execution engine
            coordinator.py      # Multi-phase orchestration
        approvals/
            __init__.py
            policy.py           # ApprovalPolicy, policies
            manager.py          # ApprovalManager with proper async
            safety.py           # Command safety classification
        state/
            __init__.py
            persistence.py      # State serialization
            repository.py       # State repository (file-based)
        contracts/
            __init__.py
            workflow.py         # Workflow interfaces
            provider.py         # Provider interfaces
            plugin.py           # Plugin interfaces
        errors/
            __init__.py
            base.py             # Base error types
            codes.py            # Error codes enum

    providers/
        __init__.py
        github/
            __init__.py
            client.py           # GitHub API client
            models.py           # GitHub data models
            auth.py             # Token management
        git/
            __init__.py
            client.py           # Git operations
            models.py           # Git data models
        llm/
            __init__.py
            client.py           # LLM client abstraction
            models.py           # LLM data models
            gemini.py           # Gemini implementation
            openai.py           # OpenAI fallback
        registry.py             # Provider registry

    intelligence/
        __init__.py
        repository/
            __init__.py
            detector.py         # Stack/language detection
            analyzer.py         # Repository structure analysis
            patterns.py         # Common pattern detection
        documentation/
            __init__.py
            generator.py        # START_HERE.md generation
            starter.py          # Getting-started guides
        issue_analysis/
            __init__.py
            classifier.py       # Issue type classification
            requirements.py     # Requirements extraction
        dependency_analysis/
            __init__.py
            scanner.py          # Dependency detection
            graph.py            # Dependency graph

    services/
        __init__.py
        discovery/
            __init__.py
            discoverer.py       # Repository/issue discovery
        mentoring/
            __init__.py
            mentor.py           # Contributor mentoring
        setup/
            __init__.py
            setup.py            # Dev environment setup
        planning/
            __init__.py
            planner.py          # Contribution planning

    plugins/
        __init__.py
        contracts.py            # Plugin base class
        registry.py             # Plugin registry
        loader.py               # Plugin loading (entry points)
        builtins/
            __init__.py

    config/
        __init__.py
        loader.py               # TOML loading (migrated from config/)
        models.py               # Pydantic config models (migrated)
        defaults.py             # Default configuration

    telemetry/
        __init__.py

    utils/
        __init__.py
        errors.py               # Shared error types
        paths.py                # Path utilities
        text.py                 # Text processing
```

### 3.2 Layer Diagram

```
┌─────────────────────────────────────────────────────┐
│                     CLI Layer                        │
│  app.py  discover  issues  analyze  explain         │
│  roadmap  mentor  docs  doctor  plugins  config      │
│  ui/ (console, themes, displays)                    │
│  prompts/                                            │
├─────────────────────────────────────────────────────┤
│                   Service Layer                      │
│  discovery/  mentoring/  setup/  planning/          │
├─────────────────────────────────────────────────────┤
│                    Core Layer                        │
│  workflow/ (state_machine, phases)                  │
│  orchestration/ (engine, coordinator)               │
│  approvals/ (policy, manager, safety)               │
│  state/ (persistence, repository)                   │
│  contracts/ (workflow, provider, plugin)            │
│  errors/ (base, codes)                              │
├─────────────────────────────────────────────────────┤
│                 Intelligence Layer                   │
│  repository/  documentation/  issue_analysis/       │
│  dependency_analysis/                                │
├─────────────────────────────────────────────────────┤
│                 Provider Layer                       │
│  github/  git/  llm/  registry                      │
├─────────────────────────────────────────────────────┤
│                 Plugin Layer                         │
│  contracts  registry  loader  builtins/             │
├─────────────────────────────────────────────────────┤
│              Config / Utils / Telemetry              │
└─────────────────────────────────────────────────────┘
```

---

## 4. Module Ownership

| Module | Owner | Responsibility |
|---|---|---|
| `cli/` | CLI team | User interaction, command definitions, output rendering |
| `core/workflow/` | Core team | State machine, phase definitions, transition validation |
| `core/orchestration/` | Core team | Workflow execution, multi-step coordination |
| `core/approvals/` | Core team | Approval policy, mutation safety, confirmation flow |
| `core/state/` | Core team | State persistence and loading |
| `core/contracts/` | Core team | Interface definitions for providers, plugins |
| `providers/github/` | Providers team | GitHub API integration (gh CLI + REST fallback) |
| `providers/git/` | Providers team | Git operations abstraction |
| `providers/llm/` | Providers team | LLM client abstraction, model-specific implementations |
| `intelligence/repository/` | Intelligence team | Stack detection, repo analysis |
| `intelligence/documentation/` | Intelligence team | Doc generation, starter guides |
| `intelligence/issue_analysis/` | Intelligence team | Issue classification, requirement extraction |
| `services/discovery/` | Services team | Repo/issue discovery workflows |
| `services/mentoring/` | Services team | Contributor guidance, mentoring |
| `plugins/` | Plugins team | Plugin API, loading, registry |
| `config/` | Config team | Config loading, models, defaults |
| `utils/` | Shared | Error types, path utilities, text processing |

---

## 5. Dependency Graph

```
CLI ──────────► Services ──────────► Core ──────────► Providers
 │                │                    │                  │
 │                │                    ├── approvals      │
 │                │                    ├── state          │
 │                │                    ├── contracts ─────┤
 │                │                    └── errors         │
 │                │                                      │
 │                └── Intelligence                       │
 │                        │                              │
 │                        ├── repository ────────────────┤
 │                        ├── documentation              │
 │                        ├── issue_analysis ────────────┤
 │                        └── dependency_analysis        │
 │                                                       │
 └── Plugins ──────────► Plugin Contracts ──────────────┘
         │
         └── Core Contracts
```

**Import Rules:**

- `cli/` → `services/`, `plugins/`, `config/`, `core/errors/`, `utils/`
- `services/` → `core/`, `providers/`, `intelligence/`
- `core/` → `providers/` (via contracts only), `config/`
- `providers/` → `config/`, `utils/`
- `intelligence/` → `providers/`, `config/`
- `plugins/` → `core/contracts/`, `config/`

**No circular imports.** Every cycle must be broken through contract interfaces.

---

## 6. Workflow State Machine

### 6.1 States

```
                    ┌────────────────────┐
                    │     IDLE           │
                    └────────┬───────────┘
                             │ start
                             ▼
                    ┌────────────────────┐
              ┌────►│  REPO_ANALYSIS     │◄────┐
              │     └────────┬───────────┘     │
              │              │ complete        │
              │              ▼                 │
              │     ┌────────────────────┐     │
              │     │  ISSUE_ANALYSIS    │     │
              │     └────────┬───────────┘     │
              │              │ complete        │
              │              ▼                 │
              │     ┌────────────────────┐     │
              │     │    PLANNING        │     │
              │     └────────┬───────────┘     │
              │              │ complete        │
              │              ▼                 │
        ┌─────┴─────┐ ┌────────────────────┐   │
        │  BLOCKED  │ │ IMPLEMENTATION     │   │
        └─────┬─────┘ └────────┬───────────┘   │
              │                │ complete      │
              │                ▼               │
              │       ┌────────────────────┐   │
              │       │   VERIFICATION     │───┘ (if tests fail, back to
              │       └────────┬───────────┘     IMPLEMENTATION)
              │                │ complete
              │                ▼
              │       ┌────────────────────┐
              │       │   VALIDATION       │
              │       └────────┬───────────┘
              │                │ complete
              │                ▼
              │       ┌────────────────────┐
              │       │   COMMIT_PR        │
              │       └────────┬───────────┘
              │                │ complete
              │                ▼
              │       ┌────────────────────┐
              │       │    COMPLETE        │
              │       └────────────────────┘
              │
              └─────── (resume from BLOCKED)
```

### 6.2 Transition Rules

| From | To | Trigger | Guard |
|---|---|---|---|
| `IDLE` | `REPO_ANALYSIS` | `start()` | Valid issue URL provided |
| `REPO_ANALYSIS` | `ISSUE_ANALYSIS` | `complete_phase()` | Repository analyzed |
| `ISSUE_ANALYSIS` | `PLANNING` | `complete_phase()` | Issue fetched and parsed |
| `PLANNING` | `IMPLEMENTATION` | `complete_phase()` | Plan documented |
| `IMPLEMENTATION` | `VERIFICATION` | `complete_phase()` | Files modified on feature branch |
| `VERIFICATION` | `IMPLEMENTATION` | `fail_phase()` | Tests failed, retry |
| `VERIFICATION` | `VALIDATION` | `complete_phase()` | All tests pass |
| `VALIDATION` | `COMMIT_PR` | `complete_phase()` | Changes validated against requirements |
| `COMMIT_PR` | `COMPLETE` | `complete_phase()` | PR created, user confirmed |
| Any | `BLOCKED` | `report_blocker()` | External dependency missing |
| `BLOCKED` | Previous | `resolve_blocker()` | Blocker removed |

### 6.3 State Persistence

```python
@dataclass
class WorkflowState:
    workflow_id: str          # UUID
    phase: WorkflowPhase      # Current phase enum
    issue_url: str | None
    issue_number: int | None
    branch_name: str | None
    repository_path: Path
    metadata: dict[str, Any]  # Phase-specific data
    created_at: datetime
    updated_at: datetime
    version: int              # Optimistic locking
```

Stored in `.oss-dev/workflows/{workflow_id}.json` — migrated from `BranchMemoryManager` pattern.

---

## 7. Provider Contracts

### 7.1 GitHub Provider

```python
class GitHubProvider(ABC):
    @abstractmethod
    async def fetch_issue(self, owner: str, repo: str, issue_number: int) -> Issue: ...

    @abstractmethod
    async def list_issues(self, owner: str, repo: str, state: str = "open", limit: int = 10) -> list[Issue]: ...

    @abstractmethod
    async def create_pr(self, owner: str, repo: str, title: str, body: str, head: str, base: str = "main") -> PullRequest: ...

    @abstractmethod
    async def get_pr_status(self, owner: str, repo: str, pr_number: int) -> PRStatus: ...

    @abstractmethod
    async def get_pr_comments(self, owner: str, repo: str, pr_number: int) -> list[Comment]: ...
```

### 7.2 Git Provider

```python
class GitProvider(ABC):
    @abstractmethod
    async def current_branch(self) -> str: ...

    @abstractmethod
    async def create_branch(self, name: str, base: str = "main") -> None: ...

    @abstractmethod
    async def checkout(self, branch: str) -> None: ...

    @abstractmethod
    async def commit(self, message: str, files: list[str] | None = None) -> str: ...

    @abstractmethod
    async def push(self, remote: str = "origin", branch: str | None = None) -> None: ...

    @abstractmethod
    async def diff(self, base: str | None = None, head: str | None = None) -> str: ...

    @abstractmethod
    async def status(self) -> GitStatus: ...

    @abstractmethod
    async def log(self, max_count: int = 10) -> list[Commit]: ...
```

### 7.3 LLM Provider

```python
class LLMProvider(ABC):
    @abstractmethod
    async def chat_completion(
        self,
        messages: list[Message],
        tools: list[ToolSchema] | None = None,
    ) -> AsyncGenerator[StreamEvent, None]: ...

    @abstractmethod
    async def count_tokens(self, text: str) -> int: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def context_window(self) -> int: ...
```

### 7.4 Provider Registry

```python
class ProviderRegistry:
    def register(self, name: str, provider: Any, category: ProviderCategory) -> None: ...
    def get(self, name: str, category: ProviderCategory) -> Any: ...
    def get_default(self, category: ProviderCategory) -> Any: ...
```

---

## 8. Plugin Contracts

### 8.1 Plugin Base

```python
class Plugin(ABC):
    name: str
    version: str
    description: str

    @abstractmethod
    async def initialize(self, config: Config) -> None: ...

    @abstractmethod
    async def shutdown(self) -> None: ...

    def get_commands(self) -> list[Command]: ...      # Optional: register CLI commands
    def get_tools(self) -> list[Tool]: ...             # Optional: register tools
    def get_hooks(self) -> dict[str, HookHandler]: ... # Optional: register hooks
```

### 8.2 Plugin Discovery

Plugins are discovered via:
1. **Entry points** — `oss_dev.plugins` entry point group in `pyproject.toml`
2. **Built-in** — `plugins/builtins/` directory
3. **User-installed** — `~/.config/oss-dev/plugins/` directory

### 8.3 Plugin Lifecycle

```
LOAD → VALIDATE → INITIALIZE → [REGISTER] → SHUTDOWN
```

---

## 9. Config Architecture

### 9.1 Layer Hierarchy

```
1. System config:  /etc/xdg/oss-dev/config.toml       (lowest priority)
2. User config:    ~/.config/oss-dev/config.toml
3. Project config: $PROJECT/.oss-dev/config.toml
4. Env vars:       OSS_DEV_*                           (highest priority)
```

### 9.2 Config Model

```python
class Config(BaseModel):
    model: ModelConfig
    cwd: Path
    approval: ApprovalPolicy
    github: GitHubConfig
    plugins: PluginConfig
    telemetry: TelemetryConfig
```

### 9.3 Key Design Decisions

- Pydantic models with strict validation
- Config loading is deterministic (no side effects)
- Sensitive values from env vars only (never logged)
- Schema version for migration support

---

## 10. Approval Architecture

### 10.1 Flow

```
Tool Execution Request
    │
    ▼
Is mutating? ──NO──► Execute (auto-approved)
    │
    YES
    │
    ▼
Check policy:
    │
    ├── NEVER       → Auto-approve safe, reject all else
    ├── ON_REQUEST  → Request user confirmation
    ├── ON_FAILURE  → Auto-approve, notify on failure
    ├── AUTO        → Auto-approve all
    └── YOLO        → Bypass all checks (not recommended)
    │
    ▼
Command safety check:
    │
    ├── Dangerous   → REJECT (blacklist patterns)
    ├── Safe        → APPROVE (whitelist patterns)
    └── Unknown     → Depends on policy
    │
    ▼
Path safety check:
    │
    ├── Inside cwd  → APPROVE
    └── Outside cwd → NEEDS_CONFIRMATION
    │
    ▼
User Confirmation (if needed) → Async prompt via CLI
```

### 10.2 Key Design Changes

- **Async confirmation callbacks** — Replace synchronous `Callable` with async protocol
- **No dangerous defaults** — `request_confirmation` must raise if no callback registered
- **Audit log** — Every approval decision logged (time, tool, decision, context)
- **Policy scoping** — Per-tool policy overrides

---

## 11. Error Handling Strategy

### 11.1 Error Types

```python
class OssDevError(Exception):          # Base
class ConfigError(OssDevError):        # Configuration
class WorkflowError(OssDevError):      # Workflow
class ProviderError(OssDevError):      # Provider
class ApprovalError(OssDevError):      # Approval
class PluginError(OssDevError):        # Plugin
class StateError(OssDevError):         # State
```

### 11.2 Error Codes

```python
class ErrorCode(str, Enum):
    CONFIG_NOT_FOUND = "CONFIG_NOT_FOUND"
    CONFIG_INVALID = "CONFIG_INVALID"
    WORKFLOW_INVALID_TRANSITION = "WORKFLOW_INVALID_TRANSITION"
    WORKFLOW_PHASE_FAILED = "WORKFLOW_PHASE_FAILED"
    PROVIDER_NOT_FOUND = "PROVIDER_NOT_FOUND"
    PROVIDER_AUTH_FAILED = "PROVIDER_AUTH_FAILED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    APPROVAL_NOT_CONFIGURED = "APPROVAL_NOT_CONFIGURED"
    PLUGIN_LOAD_FAILED = "PLUGIN_LOAD_FAILED"
    STATE_CORRUPTED = "STATE_CORRUPTED"
    STATE_VERSION_MISMATCH = "STATE_VERSION_MISMATCH"
```

### 11.3 CLI Error Display

All errors propagate to CLI layer where they are:
- Displayed with Rich (colored, formatted)
- Include error code for debugging
- Suggest resolution steps
- Never show raw stack traces to end users

---

## 12. Migration Strategy

### 12.1 Principles

1. **Working baseline preserved** — Each migration step must maintain a passing test suite
2. **Parallel run capability** — Old and new structures coexist during migration
3. **Feature parity gates** — Each phase must match existing functionality before proceeding
4. **Test-driven migration** — Write tests first, migrate code second

### 12.2 Migration Phases

| Step | What | Risk | Verification |
|---|---|---|---|
| 1. Create `src/oss_dev/` layout | Package scaffolding | Low | `uv run python -c "import oss_dev"` |
| 2. Migrate config | `config/` → `oss_dev/config/` | Low | Config tests pass |
| 3. Migrate core contracts | Define interfaces | Low | Imports work |
| 4. Migrate core/errors | Error hierarchy | Low | Error tests pass |
| 5. Migrate core/state | State persistence | Medium | State round-trip tests pass |
| 6. Migrate provider interfaces | Contracts defined | Medium | Interface tests pass |
| 7. Migrate approvals | Async approval flow | HIGH | Approval flow tests pass |
| 8. Migrate workflow engine | State machine | HIGH | Workflow transition tests pass |
| 9. Migrate CLI layer | Typer rewrite | HIGH | CLI tests pass |
| 10. Migrate services | Service layer | Medium | Integration tests pass |
| 11. Migrate intelligence | Analysis modules | Medium | Analysis tests pass |
| 12. Migrate plugins | Plugin system | Medium | Plugin loading tests pass |
| 13. Remove old packages | Cleanup | Medium | All tests pass |
| 14. Governance docs | Documentation | Low | Review |

### 12.3 Coexistence Pattern

During migration, `pyproject.toml` includes both:
```toml
[tool.setuptools.packages.find]
include = [
    "oss_dev*",
    "oss*",
    "cli*",
    "config*",
    ...
]
```

The old `main.py` entry point is preserved until complete migration. New `oss_dev` CLI entry point is added alongside.

### 12.4 Rollback Plan

If a migration step breaks tests:
1. Revert the specific package change
2. Keep the `src/oss_dev/` scaffold (it's harmless)
3. Fix the issue in isolation
4. Re-apply with fix

---

## Appendix A: CLI Command Architecture

```
oss-dev
├── discover [repo|issues]    # Discover repositories or issues
├── issues [list|search]      # Manage issues
├── analyze [repo|issue]      # Analyze repository or issue
├── explain [path]            # Explain code
├── roadmap                   # Show contribution roadmap
├── mentor [start|resume]     # Contributor mentoring
├── docs [serve|generate]     # Documentation
├── doctor                    # System diagnostics
├── plugins [list|install]    # Plugin management
└── config [get|set|show]     # Configuration
```

All commands share:
- `--help` with detailed usage
- Rich-formatted output
- Consistent exit codes (0 success, 1 error, 2 CLI error)
- JSON output option (`--json`)

---

## Appendix B: Data Flow (End-to-End)

```
User runs: oss-dev discover issues --good-first

1. CLI layer parses args, validates
2. Service layer (DiscoveryService) called
3. Core orchestration creates workflow
4. Provider layer (GitHubProvider) fetches issues
5. Intelligence layer classifies issues
6. Results flow back through layers
7. CLI renders rich output
```

```
User runs: oss-dev mentor start https://github.com/owner/repo/issues/123

1. CLI creates mentoring session
2. Workflow initialized: IDLE → REPO_ANALYSIS
3. GitProvider clones/opens repo
4. RepositoryAnalyzer analyzes structure
5. IssueAnalyzer fetches and classifies issue
6. Planner generates contribution plan
7. Workflow advances through phases
8. User guided through each step
9. Approval gates at mutation points
10. Final PR created with user confirmation
```

---

## Appendix C: Performance Targets

| Operation | Target | Measurement |
|---|---|---|
| Config load | < 100ms | pytest benchmark |
| Workflow state load | < 50ms | pytest benchmark |
| CLI startup | < 500ms | `time oss-dev --help` |
| Issue fetch (cached) | < 1s | Integration test |
| Issue fetch (API) | < 5s | Integration test |
| Plugin load (10 plugins) | < 200ms | Plugin test |

---

*This document is the authoritative architecture reference for OSS-Dev. All changes must be consistent with this blueprint. Last updated: 2026-05-16.*
