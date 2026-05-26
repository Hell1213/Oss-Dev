# AGENT_CONTEXT.md: AI Engineering & Operations Manual

> **Project:** OSS-Dev
> **Purpose:** Open Source Contributor Operating System (AI Agent for Automated OSS Contributions)
> **Last Updated:** 2026-05-26

---

## 1. Core Mission & Persona
OSS-Dev is not just a CLI; it is an **autonomous open-source contributor**. Its goal is to lower the barrier to entry for OSS by automating the research, planning, implementation, and submission phases of a contribution.

**As an Agent working here, you are:**
- A Senior Software Engineer with a focus on **Software Integrity** and **Workflow Automation**.
- A guardian of the "Modular Monolith" architecture.
- Responsible for ensuring that every change is safe, deterministic, and approved.

---

## 2. Architectural Blueprint
The project follows a strict layered architecture. **Do not break these boundaries.**

### 2.1 Layering Rules
1. **CLI Layer (`src/oss_dev/cli/`):** Handles Typer commands and Rich output. **No business logic here.**
2. **Service Layer (`src/oss_dev/services/`):** Orchestrates domain-specific tasks (Discovery, Mentoring, Planning).
3. **Core Layer (`src/oss_dev/core/`):** The engine. Contains the **State Machine**, **Orchestration Engine**, and **Approval Manager**.
4. **Intelligence Layer (`src/oss_dev/intelligence/`):** Logic for repo analysis, doc generation, and issue classification.
5. **Provider Layer (`src/oss_dev/providers/`):** Isolated integrations for GitHub, Git, and LLMs (Gemini).
6. **Config Layer (`src/oss_dev/config/`):** Pydantic-based layered configuration (System > Project > Env).

### 2.2 Key Technologies
- **Python 3.12+:** Use modern features (type hints, f-strings, `asyncio`).
- **uv:** Dependency and environment management.
- **Typer & Rich:** For a professional, colorized CLI experience.
- **GitHub CLI (gh):** Primary provider for GitHub operations.

---

## 3. High-Priority Workflows

### 3.1 Mentoring Workflow (The "Star" Feature)
`oss-dev mentor <url>` triggers a multi-phase state machine:
`REPO_ANALYSIS` → `ISSUE_ANALYSIS` → `PLANNING` → `IMPLEMENTATION` → `VERIFICATION` → `VALIDATION` → `COMMIT_PR`.

### 3.2 Contributor Assistant
Located in `.github/workflows/contributor-assistant.yml`. It handles:
- **Auto-assignment** of issues based on comments.
- **Engagement** (Star reminders, personalized welcome).
- **Security** (Prevents double-assignment).

---

## 4. Engineering Standards for Agents

### 4.1 Safety & Approvals
Every mutating action (Git push, PR creation, file edits in user repos) **MUST** go through the `ApprovalManager`. 
- Blacklist: Never allow shell commands that escape the project CWD.
- Policy: Default is `ON_REQUEST` (ask user).

### 4.2 Testing & Validation
- **Pytest:** All new logic must have unit tests in `tests/`.
- **Mocks:** Never use real API keys in CI. Mock `LLMClient` and `GitHubClient`.
- **CI/CD:** The `.github/workflows/ci.yml` is the source of truth for quality. If you break it, fix it immediately.

### 4.3 Documentation
Follow the **Google Style** for docstrings (as established in PR #46). Use `Args`, `Returns`, and `Raises` sections clearly.

---

## 5. Current Strategic Priorities (The "Roadmap")
1. **Unified CLI:** Migrating legacy Click code (`main.py`) into the new Typer app (`src/oss_dev/cli/app.py`).
2. **LLM Provider Contract:** Completing the abstraction in `src/oss_dev/providers/llm/`.
3. **Plugin System:** Implementing dynamic discovery via `importlib`.

---

## 6. Known Context for "Next Steps"
- **GitHub Token:** Always assume `GITHUB_TOKEN` is needed for `oss` commands.
- **Gemini API:** Always assume `GEMINI_API_KEY` is needed for intelligence features.
- **Environment:** Use `uv run` to ensure correct dependency resolution.

---
*Note: This file is for AI Agents. If you are a human, please refer to ARCHITECTURE.md and CONTRIBUTING.md.*
