"""Tests for label synchronization functionality."""

import json
from unittest.mock import MagicMock, patch

import pytest

from tools.label_sync import LabelManager, LabelSyncError, get_label_manager


class TestLabelManager:
  """Test suite for LabelManager class."""

  @pytest.fixture
  def manager(self) -> LabelManager:
    """Create a label manager with mock token."""
    return LabelManager("test-token")

  def test_init_with_token(self) -> None:
    """Test manager initialization with valid token."""
    manager = LabelManager("test-token")
    assert manager.token == "test-token"
    assert "Bearer test-token" in manager.headers["Authorization"]

  def test_init_without_token(self) -> None:
    """Test manager initialization fails without token."""
    with pytest.raises(ValueError):
      LabelManager("")

  def test_load_label_schema_default(self, manager: LabelManager) -> None:
    """Test loading canonical label schema from default path."""
    schema = manager.load_label_schema()

    assert isinstance(schema, list)
    assert len(schema) > 0

    label_names = {label["name"] for label in schema}
    assert "bug" in label_names
    assert "enhancement" in label_names
    assert "good first issue" in label_names

  def test_load_label_schema_custom_path(self, tmp_path) -> None:
    """Test loading schema from custom path."""
    schema_file = tmp_path / "test_labels.json"
    test_schema = {
        "labels": [
            {
                "name": "test",
                "color": "ffffff",
                "description": "Test label"
            }
        ]
    }
    schema_file.write_text(json.dumps(test_schema))

    manager = LabelManager("test-token")
    schema = manager.load_label_schema(str(schema_file))

    assert len(schema) == 1
    assert schema[0]["name"] == "test"

  def test_load_label_schema_missing_file(self, manager: LabelManager) -> None:
    """Test loading schema from non-existent file."""
    with pytest.raises(LabelSyncError):
      manager.load_label_schema("/nonexistent/path/labels.json")

  def test_load_label_schema_invalid_json(self, tmp_path) -> None:
    """Test loading schema with invalid JSON."""
    schema_file = tmp_path / "bad_labels.json"
    schema_file.write_text("not valid json {]")

    manager = LabelManager("test-token")
    with pytest.raises(LabelSyncError):
      manager.load_label_schema(str(schema_file))

  @patch("tools.label_sync.requests.get")
  def test_get_existing_labels_success(
      self, mock_get, manager: LabelManager
  ) -> None:
    """Test fetching existing labels from repository."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "name": "bug",
            "color": "d73a4a",
            "description": "Something is not working"
        },
        {
            "name": "feature",
            "color": "a2eeef",
            "description": None
        }
    ]
    mock_get.return_value = mock_response

    labels = manager.get_existing_labels("owner/repo")

    assert len(labels) == 2
    assert labels["bug"]["color"] == "d73a4a"
    assert labels["feature"]["description"] == ""

  @patch("tools.label_sync.requests.get")
  def test_get_existing_labels_api_error(
      self, mock_get, manager: LabelManager
  ) -> None:
    """Test handling of API errors when fetching labels."""
    import requests
    mock_get.side_effect = requests.RequestException("Connection timeout")

    with pytest.raises(LabelSyncError):
      manager.get_existing_labels("owner/repo")

  @patch("tools.label_sync.requests.post")
  def test_create_label_success(
      self, mock_post, manager: LabelManager
  ) -> None:
    """Test creating a new label."""
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_post.return_value = mock_response

    label = {
        "name": "bug",
        "color": "d73a4a",
        "description": "Something is not working"
    }
    result = manager.create_label("owner/repo", label)

    assert result is True
    mock_post.assert_called_once()

  @patch("tools.label_sync.requests.post")
  def test_create_label_already_exists(
      self, mock_post, manager: LabelManager
  ) -> None:
    """Test creating a label that already exists."""
    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_post.return_value = mock_response

    label = {
        "name": "bug",
        "color": "d73a4a",
        "description": "Something is not working"
    }
    result = manager.create_label("owner/repo", label)

    assert result is False

  @patch("tools.label_sync.requests.patch")
  def test_update_label_success(
      self, mock_patch, manager: LabelManager
  ) -> None:
    """Test updating an existing label."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_patch.return_value = mock_response

    new_label = {
        "name": "bug-fix",
        "color": "d73a4a",
        "description": "Bug fix"
    }
    result = manager.update_label("owner/repo", "bug", new_label)

    assert result is True
    mock_patch.assert_called_once()

  @patch("tools.label_sync.requests.delete")
  def test_delete_label_success(
      self, mock_delete, manager: LabelManager
  ) -> None:
    """Test deleting a label."""
    mock_response = MagicMock()
    mock_response.status_code = 204
    mock_delete.return_value = mock_response

    result = manager.delete_label("owner/repo", "deprecated")

    assert result is True
    mock_delete.assert_called_once()

  @patch("tools.label_sync.LabelManager.get_existing_labels")
  @patch("tools.label_sync.LabelManager.create_label")
  @patch("tools.label_sync.LabelManager.update_label")
  def test_sync_labels_new_and_update(
      self,
      mock_update,
      mock_create,
      mock_get,
      manager: LabelManager
  ) -> None:
    """Test syncing labels with creation and updates."""
    mock_get.return_value = {
        "bug": {"color": "old_color", "description": "Old description"},
        "deprecated": {"color": "ffffff", "description": "Deprecated"}
    }
    mock_create.return_value = True
    mock_update.return_value = True

    result = manager.sync_labels("owner/repo")

    assert "created" in result
    assert "updated" in result
    assert result["repo"] == "owner/repo"

  def test_get_label_manager_success(self) -> None:
    """Test creating label manager from environment."""
    with patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"}):
      manager = get_label_manager()
      assert manager.token == "test-token"

  def test_get_label_manager_missing_token(self) -> None:
    """Test label manager creation fails without token."""
    with patch.dict("os.environ", {}, clear=True):
      with pytest.raises(ValueError):
        get_label_manager()
