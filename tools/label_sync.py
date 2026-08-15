"""Label synchronization tool for standardizing labels across repositories.

Provides functionality to apply a canonical label schema uniformly across
managed repositories via the GitHub API. Ensures consistent labeling practices
for issue filtering and contributor guidance.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, cast

import requests

logger = logging.getLogger(__name__)


class LabelSyncError(Exception):
  """Raised when label synchronization fails."""

  pass


class LabelManager:
  """Manages label synchronization across GitHub repositories."""

  def __init__(self, github_token: str):
    """Initialize the label manager with GitHub credentials.

    Args:
      github_token: GitHub personal access token with repo label management
    """
    if not github_token:
      raise ValueError("GITHUB_TOKEN environment variable is required")

    self.token = github_token
    self.headers = {"Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github.v3+json"}
    self.base_url = "https://api.github.com"

  def load_label_schema(self, schema_path: str | None = None) -> list[dict]:
    """Load the canonical label schema from config.

    Args:
      schema_path: Path to labels.json config. Defaults to config/labels.json

    Returns:
      List of label definitions with name, color, and description

    Raises:
      LabelSyncError: If schema file cannot be read
    """
    if schema_path is None:
      schema_path = str(
          Path(__file__).parent.parent / "config" / "labels.json"
      )

    try:
      with open(schema_path) as f:
        config = json.load(f)
        return config.get("labels", [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
      raise LabelSyncError(f"Failed to load label schema: {e}") from e

  def get_existing_labels(self, repo: str) -> dict[str, dict]:
    """Fetch existing labels from a repository.

    Args:
      repo: Repository identifier in format "owner/repo"

    Returns:
      Dictionary mapping label names to their definitions

    Raises:
      LabelSyncError: If GitHub API request fails
    """
    try:
      url = f"{self.base_url}/repos/{repo}/labels?per_page=100"
      response = requests.get(url, headers=self.headers, timeout=10)
      response.raise_for_status()

      labels = {}
      for label in response.json():
        labels[label["name"]] = {
            "color": label["color"],
            "description": label["description"] or "",
        }

      return labels
    except requests.RequestException as e:
      raise LabelSyncError(f"Failed to fetch labels from {repo}: {e}") from e

  def create_label(self, repo: str, label: dict) -> bool:
    """Create a new label in a repository.

    Args:
      repo: Repository identifier in format "owner/repo"
      label: Label definition with name, color, and description

    Returns:
      True if label was created, False if it already exists

    Raises:
      LabelSyncError: If GitHub API request fails
    """
    try:
      url = f"{self.base_url}/repos/{repo}/labels"
      payload = {
          "name": label["name"],
          "color": label["color"],
          "description": label.get("description", ""),
      }

      response = requests.post(
          url, json=payload, headers=self.headers, timeout=10
      )

      if response.status_code == 201:
        logger.info(f"Created label '{label['name']}' in {repo}")
        return True
      elif response.status_code == 422:
        logger.debug(f"Label '{label['name']}' already exists in {repo}")
        return False
      else:
        response.raise_for_status()
        return True

    except requests.RequestException as e:
      raise LabelSyncError(
          f"Failed to create label in {repo}: {e}"
      ) from e

  def update_label(self, repo: str, old_name: str, new_label: dict) -> bool:
    """Update an existing label in a repository.

    Args:
      repo: Repository identifier in format "owner/repo"
      old_name: Current label name
      new_label: Updated label definition

    Returns:
      True if label was updated

    Raises:
      LabelSyncError: If GitHub API request fails
    """
    try:
      url = f"{self.base_url}/repos/{repo}/labels/{old_name}"
      payload = {
          "new_name": new_label["name"],
          "color": new_label["color"],
          "description": new_label.get("description", ""),
      }

      response = requests.patch(
          url, json=payload, headers=self.headers, timeout=10
      )
      response.raise_for_status()

      logger.info(f"Updated label '{old_name}' to '{new_label['name']}' in {repo}")
      return True

    except requests.RequestException as e:
      raise LabelSyncError(
          f"Failed to update label in {repo}: {e}"
      ) from e

  def delete_label(self, repo: str, name: str) -> bool:
    """Delete a label from a repository.

    Args:
      repo: Repository identifier in format "owner/repo"
      name: Label name to delete

    Returns:
      True if label was deleted

    Raises:
      LabelSyncError: If GitHub API request fails
    """
    try:
      url = f"{self.base_url}/repos/{repo}/labels/{name}"
      response = requests.delete(url, headers=self.headers, timeout=10)

      if response.status_code == 204:
        logger.info(f"Deleted label '{name}' from {repo}")
        return True
      else:
        response.raise_for_status()
        return True

    except requests.RequestException as e:
      raise LabelSyncError(
          f"Failed to delete label from {repo}: {e}"
      ) from e

  def sync_labels(self, repo: str, remove_unknown: bool = False) -> dict[str, Any]:
    """Synchronize repository labels with canonical schema.

    Applies canonical labels to the specified repository. Optionally removes
    labels not in the canonical schema. Idempotent operation.

    Args:
      repo: Repository identifier in format "owner/repo"
      remove_unknown: If True, delete labels not in canonical schema

    Returns:
      Sync result summary with created, updated, and deleted label counts

    Raises:
      LabelSyncError: If synchronization fails
    """
    logger.info(f"Syncing labels for {repo}")

    canonical = self.load_label_schema()
    canonical_names = {label["name"] for label in canonical}
    existing = self.get_existing_labels(repo)

    result: dict[str, Any] = {
        "repo": repo,
        "created": cast(list[str], []),
        "updated": cast(list[str], []),
        "deleted": cast(list[str], []),
        "unchanged": cast(list[str], []),
    }

    for label in canonical:
      name = label["name"]

      if name in existing:
        existing_label = existing[name]
        if (existing_label["color"] != label["color"] or
            existing_label["description"] != label.get("description", "")):
          self.update_label(repo, name, label)
          result["updated"].append(name)
        else:
          result["unchanged"].append(name)
      else:
        self.create_label(repo, label)
        result["created"].append(name)

    if remove_unknown:
      for existing_name in existing:
        if existing_name not in canonical_names:
          self.delete_label(repo, existing_name)
          result["deleted"].append(existing_name)

    logger.info(
        f"Sync complete for {repo}: "
        f"+{len(result['created'])} ~{len(result['updated'])} "
        f"-{len(result['deleted'])}"
    )

    return result

  def sync_multiple_repos(
      self, repos: list[str], remove_unknown: bool = False
  ) -> dict[str, dict[str, Any]]:
    """Synchronize labels across multiple repositories.

    Args:
      repos: List of repository identifiers (owner/repo format)
      remove_unknown: If True, delete non-canonical labels

    Returns:
      Mapping of repository names to sync results

    Raises:
      LabelSyncError: If any synchronization fails
    """
    results = {}

    for repo in repos:
      try:
        results[repo] = self.sync_labels(repo, remove_unknown)
      except LabelSyncError as e:
        logger.error(f"Failed to sync {repo}: {e}")
        results[repo] = {"error": str(e)}

    return results


def get_label_manager() -> LabelManager:
  """Create a label manager instance with GitHub credentials.

  Reads GITHUB_TOKEN from environment variables.

  Returns:
    Initialized LabelManager instance

  Raises:
    ValueError: If GITHUB_TOKEN is not set
  """
  token = os.getenv("GITHUB_TOKEN")
  if not token:
    raise ValueError(
        "GITHUB_TOKEN environment variable is required for label operations"
    )

  return LabelManager(token)
