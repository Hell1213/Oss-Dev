"""Review Session — shared state model for contributor + reviewer agents.

This module implements the shared session that both the contributor agent
and the PR reviewer agent read from and write to. Instead of sharing a
context window (expensive), they share a structured state file. The
contributor writes its phase trail (plan, changed files, test results).
The reviewer reads that trail and produces a structured review verdict.

Storage: .oss-dev/reviews/{pr_number}.json
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ReviewVerdict(str, Enum):
    """Possible review verdicts."""

    APPROVED = "approved"
    REQUEST_CHANGES = "request_changes"
    REJECT = "reject"
    PENDING = "pending"


class ReviewerRole(str, Enum):
    """Agent role in a review session."""

    CONTRIBUTOR = "contributor"
    REVIEWER = "reviewer"


@dataclass
class ContributorArtifact:
    """Artifacts written by the contributor agent during its workflow."""

    issue_url: str | None = None
    issue_number: int | None = None
    issue_title: str | None = None
    branch_name: str | None = None
    plan: str | None = None
    changed_files: list[str] = field(default_factory=list)
    test_command: str | None = None
    test_results: str | None = None
    tests_passed: bool = False
    commit_sha: str | None = None
    pr_url: str | None = None
    pr_number: int | None = None
    phase_trail: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SlopIndicator:
    """A single AI slop detection signal."""

    check_name: str
    severity: str  # "info", "warning", "critical"
    description: str
    affected_files: list[str] = field(default_factory=list)
    metric_value: float | int | str | None = None


@dataclass
class FileReview:
    """Per-file review findings."""

    file_path: str
    verdict: str  # "clean", "needs_changes", "reject"
    findings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class ReviewerFinding:
    """Findings written by the reviewer agent."""

    verdict: ReviewVerdict = ReviewVerdict.PENDING
    summary: str = ""
    slop_indicators: list[SlopIndicator] = field(default_factory=list)
    file_reviews: list[FileReview] = field(default_factory=list)
    overall_quality_score: float = 0.0  # 0.0 to 1.0
    is_ai_slop: bool = False
    slop_confidence: float = 0.0  # 0.0 to 1.0
    recommendations: list[str] = field(default_factory=list)
    reviewed_at: datetime = field(default_factory=datetime.now)


@dataclass
class ReviewSession:
    """Shared state between contributor and reviewer agents.

    Attributes:
        session_id: UUID for the review session.
        pr_url: GitHub PR URL.
        pr_number: PR number.
        repo: Repository in owner/repo format.
        contributor: Artificts from the contributor agent.
        reviewer: Findings from the reviewer agent.
        created_at: When the session was created.
        updated_at: Last update timestamp.
    """

    session_id: str = ""
    pr_url: str = ""
    pr_number: int | None = None
    repo: str = ""
    issue_context: dict[str, Any] = field(default_factory=dict)
    contributor: ContributorArtifact = field(default_factory=ContributorArtifact)
    reviewer: ReviewerFinding = field(default_factory=ReviewerFinding)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def save(self, base_dir: Path | None = None) -> Path:
        """Save the review session to disk.

        Args:
            base_dir: Directory to store the session file. Defaults to
                .oss-dev/reviews/ in the current working directory.

        Returns:
            Path to the saved file.
        """
        reviews_dir = base_dir or (Path.cwd() / ".oss-dev" / "reviews")
        reviews_dir.mkdip(parents=True, exist_ok=True)

        pr_num = self.pr_number or "unknown"
        file_path = reviews_dir / f"{pr_num}.json"

        data = self._to_dict()
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Review session saved: {file_path}")
        return file_path

    @classmethod
    def load(cls, pr_number: int, base_dir: Path | None = None) -> ReviewSession | None:
        """Load a review session from disk.

        Args:
            pr_number: PR number to load.
            base_dir: Directory containing session files.

        Returns:
            ReviewSession instance, or None if not found.
        """
        reviews_dir = base_dir or (Path.cwd() / ".oss-dev" / "reviews")
        file_path = reviews_dir / f"{pr_number}.json"

        if not file_path.exists():
            return None

        with open(file_path) as f:
            data = json.load(f)

        return cls._from_dict(data)

    def update_contributor(self, **kwargs: Any) -> None:
        """Update contributor artifacts.

        Args:
            **kwargs: Fields to update on ContributorArtifact.
        """
        for key, value in kwargs.items():
            if hasattr(self.contributor, key):
                setattr(self.contributor, key, value)
        self.updated_at = datetime.now()

    def update_reviewer(self, **kwargs: Any) -> None:
        """Update reviewer findings.

        Args:
            **kwargs: Fields to update on ReviewerFinding.
        """
        for key, value in kwargs.items():
            if hasattr(self.reviewer, key):
                setattr(self.reviewer, key, value)
        self.reviewer.reviewed_at = datetime.now()
        self.updated_at = datetime.now()

    def add_phase_trail(self, phase: str, status: str, details: str = "") -> None:
        """Add a phase trail entry.

        Args:
            phase: Workflow phase name.
            status: "started", "completed", "failed".
            details: Optional details string.
        """
        self.contributor.phase_trail.append({
            "phase": phase,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        })
        self.updated_at = datetime.now()

    def _to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        data = asdict(self)
        # Convert enums to strings
        data["reviewer"]["verdict"] = self.reviewer.verdict.value
        return data

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> ReviewSession:
        """Deserialize from a dict."""
        contributor_data = data.get("contributor", {})
        reviewer_data = data.get("reviewer", {})

        # Reconstruct enums
        verdict_str = reviewer_data.get("verdict", "pending")
        try:
            verdict = ReviewVerdict(verdict_str)
        except ValueError:
            verdict = ReviewVerdict.PENDING

        # Reconstruct slop indicators
        slop_indicators = [
            SlopIndicator(
                check_name=s.get("check_name", ""),
                severity=s.get("severity", "info"),
                description=s.get("description", ""),
                affected_files=s.get("affected_files", []),
                metric_value=s.get("metric_value"),
            )
            for s in reviewer_data.get("slop_indicators", [])
        ]

        # Reconstruct file reviews
        file_reviews = [
            FileReview(
                file_path=fr.get("file_path", ""),
                verdict=fr.get("verdict", "clean"),
                findings=fr.get("findings", []),
                suggestions=fr.get("suggestions", []),
            )
            for fr in reviewer_data.get("file_reviews", [])
        ]

        contributor = ContributorArtifact(
            issue_url=contributor_data.get("issue_url"),
            issue_number=contributor_data.get("issue_number"),
            issue_title=contributor_data.get("issue_title"),
            branch_name=contributor_data.get("branch_name"),
            plan=contributor_data.get("plan"),
            changed_files=contributor_data.get("changed_files", []),
            test_command=contributor_data.get("test_command"),
            test_results=contributor_data.get("test_results"),
            tests_passed=contributor_data.get("tests_passed", False),
            commit_sha=contributor_data.get("commit_sha"),
            pr_url=contributor_data.get("pr_url"),
            pr_number=contributor_data.get("pr_number"),
            phase_trail=contributor_data.get("phase_trail", []),
        )

        reviewer = ReviewerFinding(
            verdict=verdict,
            summary=reviewer_data.get("summary", ""),
            slop_indicators=slop_indicators,
            file_reviews=file_reviews,
            overall_quality_score=reviewer_data.get("overall_quality_score", 0.0),
            is_ai_slop=reviewer_data.get("is_ai_slop", False),
            slop_confidence=reviewer_data.get("slop_confidence", 0.0),
            recommendations=reviewer_data.get("recommendations", []),
        )

        return cls(
            session_id=data.get("session_id", ""),
            pr_url=data.get("pr_url", ""),
            pr_number=data.get("pr_number"),
            repo=data.get("repo", ""),
            issue_context=data.get("issue_context", {}),
            contributor=contributor,
            reviewer=reviewer,
        )
