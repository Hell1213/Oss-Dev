"""Tests for interactive onboarding checklist system."""

import json
from pathlib import Path

import pytest

from tools.onboarding import OnboardingChecklist, OnboardingStep


class TestOnboardingStep:
  """Test suite for OnboardingStep class."""

  def test_create_step(self) -> None:
    """Test creating an onboarding step."""
    step = OnboardingStep(
        id="test",
        title="Test Step",
        description="A test step",
        guidance="Do this and that",
        resources=[{"title": "Guide", "url": "http://example.com"}],
    )

    assert step.id == "test"
    assert step.title == "Test Step"
    assert not step.completed
    assert step.completed_at is None

  def test_step_to_dict(self) -> None:
    """Test converting step to dictionary."""
    step = OnboardingStep(
        id="test",
        title="Test",
        description="Desc",
        guidance="Guide",
        resources=[],
        completed=True,
    )

    data = step.to_dict()
    assert data["id"] == "test"
    assert data["completed"] is True

  def test_step_from_dict(self) -> None:
    """Test creating step from dictionary."""
    data = {
        "id": "test",
        "title": "Test",
        "description": "Desc",
        "guidance": "Guide",
        "resources": [],
        "completed": True,
        "completed_at": "2024-01-01T00:00:00",
    }

    step = OnboardingStep.from_dict(data)
    assert step.id == "test"
    assert step.completed is True


class TestOnboardingChecklist:
  """Test suite for OnboardingChecklist class."""

  @pytest.fixture
  def checklist(self, tmp_path: Path) -> OnboardingChecklist:
    """Create a temporary checklist for testing."""
    storage_path = str(tmp_path / "onboarding.json")
    return OnboardingChecklist(storage_path)

  def test_initialize_new_checklist(self, checklist: OnboardingChecklist) -> None:
    """Test creating a new checklist."""
    assert len(checklist.steps) > 0
    assert all(not step.completed for step in checklist.steps)

  def test_default_steps_present(self, checklist: OnboardingChecklist) -> None:
    """Test that all default steps are present."""
    step_ids = {step.id for step in checklist.steps}

    expected_ids = {
        "fork-clone",
        "install-dependencies",
        "read-guidelines",
        "find-issue",
        "create-branch",
        "implement-fix",
        "create-pr",
        "join-community",
    }

    assert expected_ids.issubset(step_ids)

  def test_complete_step(self, checklist: OnboardingChecklist) -> None:
    """Test marking a step as complete."""
    assert checklist.complete_step("fork-clone")

    step = checklist.get_step("fork-clone")
    assert step is not None
    assert step.completed is True
    assert step.completed_at is not None

  def test_complete_nonexistent_step(self, checklist: OnboardingChecklist) -> None:
    """Test completing a non-existent step."""
    result = checklist.complete_step("nonexistent")
    assert result is False

  def test_uncomplete_step(self, checklist: OnboardingChecklist) -> None:
    """Test marking a step as incomplete."""
    checklist.complete_step("fork-clone")
    assert checklist.uncomplete_step("fork-clone")

    step = checklist.get_step("fork-clone")
    assert step is not None
    assert step.completed is False
    assert step.completed_at is None

  def test_get_step(self, checklist: OnboardingChecklist) -> None:
    """Test retrieving a specific step."""
    step = checklist.get_step("fork-clone")

    assert step is not None
    assert step.id == "fork-clone"
    assert "Fork" in step.title

  def test_get_nonexistent_step(self, checklist: OnboardingChecklist) -> None:
    """Test getting a step that doesn't exist."""
    step = checklist.get_step("nonexistent")
    assert step is None

  def test_get_progress_initial(self, checklist: OnboardingChecklist) -> None:
    """Test progress tracking for new checklist."""
    progress = checklist.get_progress()

    assert progress["completed"] == 0
    assert progress["total"] > 0
    assert progress["percentage"] == 0
    assert not progress["all_complete"]
    assert progress["next_step"] is not None

  def test_get_progress_partial(self, checklist: OnboardingChecklist) -> None:
    """Test progress tracking with partial completion."""
    checklist.complete_step("fork-clone")
    checklist.complete_step("install-dependencies")

    progress = checklist.get_progress()

    assert progress["completed"] == 2
    assert progress["percentage"] > 0
    assert not progress["all_complete"]

  def test_get_progress_complete(self, checklist: OnboardingChecklist) -> None:
    """Test progress tracking when all steps complete."""
    for step in checklist.steps:
      checklist.complete_step(step.id)

    progress = checklist.get_progress()

    assert progress["completed"] == progress["total"]
    assert progress["percentage"] == 100
    assert progress["all_complete"]
    assert progress["next_step"] is None

  def test_save_and_load_progress(self, tmp_path: Path) -> None:
    """Test saving and loading progress."""
    storage_path = str(tmp_path / "onboarding.json")

    # Create and modify a checklist
    checklist1 = OnboardingChecklist(storage_path)
    checklist1.complete_step("fork-clone")
    checklist1.complete_step("install-dependencies")

    # Load the same checklist
    checklist2 = OnboardingChecklist(storage_path)

    # Verify progress is loaded
    assert checklist2.get_step("fork-clone").completed
    assert checklist2.get_step("install-dependencies").completed
    assert not checklist2.get_step("read-guidelines").completed

  def test_reset_progress(self, checklist: OnboardingChecklist) -> None:
    """Test resetting all progress."""
    # Mark several steps as complete
    for step_id in ["fork-clone", "install-dependencies", "read-guidelines"]:
      checklist.complete_step(step_id)

    # Reset
    checklist.reset_progress()

    # Verify all are incomplete
    progress = checklist.get_progress()
    assert progress["completed"] == 0

  def test_storage_directory_created(self, tmp_path: Path) -> None:
    """Test that storage directory is created if it doesn't exist."""
    storage_path = str(tmp_path / "nested" / "dir" / "onboarding.json")
    checklist = OnboardingChecklist(storage_path)

    checklist.complete_step("fork-clone")
    assert Path(storage_path).exists()
    assert Path(storage_path).parent.exists()

  def test_saved_progress_structure(self, tmp_path: Path) -> None:
    """Test the structure of saved progress."""
    storage_path = str(tmp_path / "onboarding.json")
    checklist = OnboardingChecklist(storage_path)

    checklist.complete_step("fork-clone")
    checklist.save_progress()

    # Load and verify structure
    with open(storage_path) as f:
      data = json.load(f)

    assert "version" in data
    assert "created_at" in data
    assert "steps" in data
    assert len(data["steps"]) > 0
    assert data["steps"][0]["completed"] is True

  def test_default_storage_path(self) -> None:
    """Test that default storage path is set correctly."""
    checklist = OnboardingChecklist()
    assert ".oss-dev" in str(checklist.storage_path)
    assert "onboarding.json" in str(checklist.storage_path)
