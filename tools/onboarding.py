"""Interactive contributor onboarding checklist system.

Provides a guided onboarding experience for new contributors with persistent
progress tracking, step-by-step guidance, and motivation through completion.
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class OnboardingStep:
  """Represents a single onboarding step."""

  id: str
  title: str
  description: str
  guidance: str
  resources: list[dict[str, str]]
  completed: bool = False
  completed_at: str | None = None

  def to_dict(self) -> dict[str, Any]:
    """Convert to dictionary representation."""
    return asdict(self)

  @classmethod
  def from_dict(cls, data: dict[str, Any]) -> "OnboardingStep":
    """Create from dictionary representation."""
    return cls(**data)


class OnboardingChecklist:
  """Manages interactive onboarding checklist with persistent progress."""

  DEFAULT_STEPS = [
      OnboardingStep(
          id="fork-clone",
          title="Fork and clone the repository",
          description="Create your own copy of the repository",
          guidance=(
              "Visit https://github.com/Hell1213/Oss-Dev and click 'Fork' "
              "in the top-right corner. Then run:\n"
              "  git clone https://github.com/YOUR_USERNAME/Oss-Dev.git\n"
              "  cd Oss-Dev\n"
              "  git remote add upstream https://github.com/Hell1213/Oss-Dev.git"
          ),
          resources=[
              {
                  "title": "GitHub Forking Guide",
                  "url": "https://guides.github.com/activities/forking/"
              }
          ],
      ),
      OnboardingStep(
          id="install-dependencies",
          title="Install dependencies and set up development environment",
          description="Get your local development environment ready",
          guidance=(
              "Make sure you have Python 3.12+ and uv installed, then run:\n"
              "  uv sync --dev\n"
              "\nFor full verification run:\n"
              "  uv run oss-dev --version\n"
              "  uv run pytest"
          ),
          resources=[
              {
                  "title": "Setup Documentation",
                  "url": "https://github.com/Hell1213/Oss-Dev#installation"
              }
          ],
      ),
      OnboardingStep(
          id="read-guidelines",
          title="Read CONTRIBUTING.md and CODE_OF_CONDUCT.md",
          description="Understand project standards and community values",
          guidance=(
              "Review these key documents:\n"
              "  - CONTRIBUTING.md — How to submit PRs\n"
              "  - CODE_OF_CONDUCT.md — Community standards\n"
              "  - ARCHITECTURE.md — Project design overview\n"
              "\nThis ensures you understand what's expected."
          ),
          resources=[
              {
                  "title": "CONTRIBUTING.md",
                  "url": "https://github.com/Hell1213/Oss-Dev/blob/main/CONTRIBUTING.md"
              },
              {
                  "title": "CODE_OF_CONDUCT.md",
                  "url": "https://github.com/Hell1213/Oss-Dev/blob/main/CODE_OF_CONDUCT.md"
              }
          ],
      ),
      OnboardingStep(
          id="find-issue",
          title="Find a 'good first issue' labeled issue",
          description="Pick a beginner-friendly issue to work on",
          guidance=(
              "Look for issues labeled 'good first issue' or 'beginner-friendly':\n"
              "  https://github.com/Hell1213/Oss-Dev/labels/good%20first%20issue\n"
              "\nRead the issue description carefully and understand what's asked.\n"
              "If you have questions, comment on the issue!"
          ),
          resources=[
              {
                  "title": "Good First Issues",
                  "url": "https://github.com/Hell1213/Oss-Dev/labels/good%20first%20issue"
              }
          ],
      ),
      OnboardingStep(
          id="create-branch",
          title="Create a feature branch",
          description="Start work on your contribution",
          guidance=(
              "Create a new branch for your work:\n"
              "  git checkout -b feat/issue-XXX-brief-description\n"
              "\nMake sure to:\n"
              "  - Keep branch names descriptive\n"
              "  - Reference the issue number (e.g., issue-123)\n"
              "  - Use lowercase with hyphens"
          ),
          resources=[
              {
                  "title": "Git Branch Guide",
                  "url": "https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging"
              }
          ],
      ),
      OnboardingStep(
          id="implement-fix",
          title="Implement your changes and run tests",
          description="Code the solution and verify it works",
          guidance=(
              "After making your changes, verify everything works:\n"
              "  uv run ruff check .\n"
              "  uv run mypy .\n"
              "  uv run pytest\n"
              "\nAll checks must pass before submitting your PR!"
          ),
          resources=[
              {
                  "title": "Testing Guide",
                  "url": "https://github.com/Hell1213/Oss-Dev#testing"
              }
          ],
      ),
      OnboardingStep(
          id="create-pr",
          title="Submit your first Pull Request",
          description="Share your contribution for review",
          guidance=(
              "Push your branch and create a PR:\n"
              "  git push -u origin feat/issue-XXX-description\n"
              "\nThen create a PR on GitHub with:\n"
              "  - Clear title referencing the issue\n"
              "  - Detailed description of changes\n"
              "  - Reference to the issue (Fixes #123)\n"
              "  - Confirmation that all tests pass\n"
              "\nBe patient during review and respond to feedback!"
          ),
          resources=[
              {
                  "title": "PULL_REQUEST_TEMPLATE.md",
                  "url": "https://github.com/Hell1213/Oss-Dev/blob/main/.github/PULL_REQUEST_TEMPLATE.md"
              }
          ],
      ),
      OnboardingStep(
          id="join-community",
          title="Join the community Discord or discussions",
          description="Connect with other contributors",
          guidance=(
              "Engage with the community:\n"
              "  - Participate in GitHub Discussions\n"
              "  - Join the Discord server if available\n"
              "  - Introduce yourself!\n"
              "\nThe community is here to help and celebrate contributions."
          ),
          resources=[
              {
                  "title": "GitHub Discussions",
                  "url": "https://github.com/Hell1213/Oss-Dev/discussions"
              }
          ],
      ),
  ]

  def __init__(self, storage_path: str | None = None):
    """Initialize the onboarding checklist.

    Args:
      storage_path: Path to store progress. Defaults to ~/.oss-dev/onboarding.json
    """
    if storage_path is None:
      storage_path = str(
          Path.home() / ".oss-dev" / "onboarding.json"
      )

    self.storage_path = Path(storage_path)
    self.steps = self._load_steps()

  def _load_steps(self) -> list[OnboardingStep]:
    """Load saved progress or create new checklist."""
    if self.storage_path.exists():
      try:
        with open(self.storage_path) as f:
          data = json.load(f)
          return [
              OnboardingStep.from_dict(step)
              for step in data.get("steps", [])
          ]
      except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Could not load saved progress: {e}")
        return [OnboardingStep(**asdict(step)) for step in self.DEFAULT_STEPS]
    else:
      return [OnboardingStep(**asdict(step)) for step in self.DEFAULT_STEPS]

  def save_progress(self) -> None:
    """Save current progress to storage."""
    self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "steps": [step.to_dict() for step in self.steps],
    }

    with open(self.storage_path, "w") as f:
      json.dump(data, f, indent=2)

    logger.info(f"Progress saved to {self.storage_path}")

  def complete_step(self, step_id: str) -> bool:
    """Mark a step as completed.

    Args:
      step_id: ID of the step to complete

    Returns:
      True if step was found and marked complete
    """
    for step in self.steps:
      if step.id == step_id:
        step.completed = True
        step.completed_at = datetime.now().isoformat()
        self.save_progress()
        return True

    return False

  def uncomplete_step(self, step_id: str) -> bool:
    """Mark a step as not completed (undo).

    Args:
      step_id: ID of the step to uncomplete

    Returns:
      True if step was found and marked incomplete
    """
    for step in self.steps:
      if step.id == step_id:
        step.completed = False
        step.completed_at = None
        self.save_progress()
        return True

    return False

  def get_step(self, step_id: str) -> OnboardingStep | None:
    """Get a specific step by ID.

    Args:
      step_id: ID of the step

    Returns:
      The OnboardingStep or None if not found
    """
    for step in self.steps:
      if step.id == step_id:
        return step

    return None

  def get_progress(self) -> dict[str, Any]:
    """Get overall progress summary.

    Returns:
      Dictionary with completion stats and next step
    """
    completed = sum(1 for step in self.steps if step.completed)
    total = len(self.steps)
    percentage = (completed / total * 100) if total > 0 else 0

    next_step = None
    for step in self.steps:
      if not step.completed:
        next_step = step
        break

    return {
        "completed": completed,
        "total": total,
        "percentage": percentage,
        "next_step": next_step,
        "all_complete": completed == total,
    }

  def reset_progress(self) -> None:
    """Reset all progress."""
    for step in self.steps:
      step.completed = False
      step.completed_at = None

    self.save_progress()
    logger.info("Progress reset")
