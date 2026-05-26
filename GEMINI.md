# Project-Specific Instructions (OSS-Dev)

## Engineering Mandates
1. **Architecture Integrity:** Strictly adhere to the layered architecture defined in `ARCHITECTURE.md`. Never import the CLI layer into Core or Providers.
2. **Type Safety:** All new Python code must have comprehensive type hints. Run `mypy` to verify.
3. **Async First:** The Core and Provider layers are primarily async. Ensure proper `await` usage in `Agent` event handlers.
4. **Approval Gates:** Any tool or function that modifies the filesystem or remote state (Git/GitHub) MUST utilize the `safety/approval.py` logic.
5. **Documentation:** Use Google-style docstrings for all public-facing functions and classes.

## CLI & UX Standards
1. **Rich Output:** Use the `rich` library for all CLI feedback. Prefer `Panel`, `Table`, and `Progress` for structured data.
2. **Error Handling:** Propagate technical errors to the CLI layer, then render them as user-friendly "Actionable Errors" using Rich.
3. **Command Parity:** When adding features to the legacy `main.py`, prioritize porting them to the new Typer-based `src/oss_dev/cli/app.py`.

## Testing Protocol
1. **Reproduction:** Before fixing a bug, create a failing test case in `tests/`.
2. **Mocks:** Utilize the fixtures in `tests/conftest.py` for mocking GitHub and Git operations.
3. **CI Alignment:** Ensure any changes to the build/test flow are reflected in `.github/workflows/ci.yml`.

## Agent-to-Agent Communication
1. **Context Update:** After significant architectural changes, update `AGENT_CONTEXT.md` to reflect the new state.
2. **Memory:** Use the private `MEMORY.md` for session-specific state, but keep `AGENT_CONTEXT.md` for permanent project knowledge.
