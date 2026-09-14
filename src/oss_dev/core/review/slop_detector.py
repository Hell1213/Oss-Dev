"""AI Slop Detection — deterministic heuristics for detecting low-quality
AI-generated contributions.

These checks run as Python code (zero tokens) and feed their results
into the LLM reviewer as structured context. The LLM then interprets
the signals — but the detection itself is deterministic and cheap.

Usage:
    from src.oss_dev.core.review.slop_detector import SlopDetector

    detector = SlopDetector(diff_text, changed_files, issue_body)
    results = detector.run_all_checks()
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Reuse the SlopIndicator from review_session
from src.oss_dev.core.state.review_session import SlopIndicator


@dataclass
class SlopReport:
    """Aggregated AI slop detection report."""

    indicators: list[SlopIndicator] = field(default_factory=list)
    slop_score: float = 0.0  # 0.0 (clean) to 1.0 (definitely slop)
    is_likely_slop: bool = False

    def add(
        self,
        check_name: str,
        severity: str,
        description: str,
        affected_files: list[str] | None = None,
        metric_value: float | int | str | None = None,
    ) -> None:
        """Add a slop indicator to the report."""
        self.indicators.append(
            SlopIndicator(
                check_name=check_name,
                severity=severity,
                description=description,
                affected_files=affected_files or [],
                metric_value=metric_value,
            )
        )


class SlopDetector:
    """Deterministic AI slop detector.

    Runs a battery of checks on a PR diff to detect common patterns
    of low-quality AI-generated code.
    """

    def __init__(
        self,
        diff_text: str,
        changed_files: list[str],
        issue_body: str = "",
        issue_keywords: list[str] | None = None,
    ) -> None:
        self.diff = diff_text
        self.changed_files = changed_files
        self.issue_body = issue_body.lower()
        self.issue_keywords = issue_keywords or self._extract_keywords(issue_body)

        # Parse diff into per-file hunks
        self.file_diffs: dict[str, str] = self._parse_diff(diff_text)

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from the issue body."""
        if not text:
            return []
        # Simple keyword extraction: words > 4 chars, not stopwords
        stopwords = {
            "the", "this", "that", "with", "from", "have", "should",
            "would", "could", "there", "their", "where", "which",
            "when", "what", "they", "them", "then", "than", "also",
            "been", "were", "will", "into", "about", "after", "before",
            "being", "issue", "please", "using", "based",
        }
        words = re.findall(r"[a-zA-Z_]{5,}", text.lower())
        return [w for w in words if w not in stopwords]

    def _parse_diff(self, diff_text: str) -> dict[str, str]:
        """Parse a unified diff into per-file sections."""
        files: dict[str, str] = {}
        current_file = None
        current_lines: list[str] = []

        for line in diff_text.splitlines():
            if line.startswith("diff --git"):
                if current_file:
                    files[current_file] = "\n".join(current_lines)
                # Extract file path from "diff --git a/path b/path"
                match = re.match(r"diff --git a/(.+?) b/(.+)", line)
                current_file = match.group(2) if match else None
                current_lines = [line]
            else:
                current_lines.append(line)

        if current_file:
            files[current_file] = "\n".join(current_lines)

        return files

    def run_all_checks(self) -> SlopReport:
        """Run all slop detection checks.

        Returns:
            SlopReport with all indicators and an aggregate slop score.
        """
        report = SlopReport()

        self._check_whitespace_only_changes(report)
        self._check_excessive_comments(report)
        self._check_formatting_only_files(report)
        self._check_scope_alignment(report)
        self._check_tautological_tests(report)
        self._check_diff_churn(report)
        self._check_boilerplate_patterns(report)
        self._check_over_engineering(report)

        # Calculate aggregate slop score
        severity_weights = {"info": 0.1, "warning": 0.3, "critical": 0.6}
        total_weight = sum(
            severity_weights.get(i.severity, 0.1) for i in report.indicators
        )
        report.slop_score = min(total_weight, 1.0)
        report.is_likely_slop = report.slop_score >= 0.5

        return report

    def _check_whitespace_only_changes(self, report: SlopReport) -> None:
        """Detect files where changes are only whitespace or import reordering."""
        for file_path, file_diff in self.file_diffs.items():
            added_lines = [
                l[1:] for l in file_diff.splitlines()
                if l.startswith("+") and not l.startswith("+++")
            ]
            removed_lines = [
                l[1:] for l in file_diff.splitlines()
                if l.startswith("-") and not l.startswith("---")
            ]

            if not added_lines and not removed_lines:
                continue

            # Check if all added lines are whitespace-only or just import changes
            ws_only = all(
                l.strip() == "" or l.strip().startswith(("import ", "from ", "#"))
                for l in added_lines
            )
            if ws_only and added_lines:
                report.add(
                    check_name="whitespace_or_import_only",
                    severity="warning",
                    description=f"File '{file_path}' has only whitespace/import changes — possible drive-by formatting",
                    affected_files=[file_path],
                    metric_value=len(added_lines),
                )

    def _check_excessive_comments(self, report: SlopReport) -> None:
        """Detect excessive new comments added to existing code."""
        comment_count = 0
        comment_files: list[str] = []

        for file_path, file_diff in self.file_diffs.items():
            file_comments = 0
            for line in file_diff.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    stripped = line[1:].strip()
                    # Python comments, JS comments, etc.
                    if stripped.startswith("#") or stripped.startswith("//"):
                        file_comments += 1

            if file_comments > 5:
                comment_count += file_comments
                comment_files.append(file_path)

        if comment_count > 10:
            report.add(
                check_name="excessive_comments",
                severity="warning",
                description=f"{comment_count} new comments added across {len(comment_files)} files — possible AI comment slop",
                affected_files=comment_files,
                metric_value=comment_count,
            )

    def _check_formatting_only_files(self, report: SlopReport) -> None:
        """Detect files where ALL changes are formatting (no logic changes)."""
        for file_path, file_diff in self.file_diffs.items():
            added = [
                l[1:] for l in file_diff.splitlines()
                if l.startswith("+") and not l.startswith("+++")
            ]
            removed = [
                l[1:] for l in file_diff.splitlines()
                if l.startswith("-") and not l.startswith("---")
            ]

            if not added and not removed:
                continue

            # Check if removed and added lines are the same after stripping
            # (pure whitespace changes)
            added_stripped = sorted(l.strip() for l in added)
            removed_stripped = sorted(l.strip() for l in removed)

            if (
                added_stripped == removed_stripped
                and len(added) == len(removed)
                and added != removed
            ):
                report.add(
                    check_name="formatting_only",
                    severity="warning",
                    description=f"File '{file_path}' has only whitespace formatting changes — no logic change",
                    affected_files=[file_path],
                    metric_value=len(added),
                )

    def _check_scope_alignment(self, report: SlopReport) -> None:
        """Check if changed files align with issue keywords."""
        if not self.issue_keywords:
            return

        # Match changed file paths against issue keywords
        aligned_files: list[str] = []
        unaligned_files: list[str] = []

        for file_path in self.changed_files:
            file_lower = file_path.lower()
            # Check if any keyword matches in the file path
            if any(kw in file_lower for kw in self.issue_keywords):
                aligned_files.append(file_path)
            else:
                unaligned_files.append(file_path)

        if unaligned_files and aligned_files:
            mismatch_ratio = len(unaligned_files) / len(self.changed_files)
            if mismatch_ratio > 0.5:
                report.add(
                    check_name="scope_mismatch",
                    severity="critical",
                    description=f"{len(unaligned_files)}/{len(self.changed_files)} changed files don't match issue keywords — possible scope creep",
                    affected_files=unaligned_files,
                    metric_value=f"{mismatch_ratio:.0%}",
                )

    def _check_tautological_tests(self, report: SlopReport) -> None:
        """Detect tests that assert trivially without testing real behavior."""
        tautological_patterns = [
            r"assert\s+True",
            r"assert\s+is\s+not\s+None\s*$",
            r"assert\s+\w\\s+is\s+not\s+None\s*$",
            r"pass\s*$",
        ]

        test_files = [
            f for f in self.changed_files
            if "test" in f.lower() or f.endswith(("_test.py", ".test.js", ".spec.ts"))
        ]
        if not test_files:
            return

        tautological_count = 0
        for file_path in test_files:
            file_diff = self.file_diffs.get(file_path, "")
            for pattern in tautological_patterns:
                matches = re.findall(pattern, file_diff, re.MULTILINE)
                tautological_count += len(matches)

        if tautological_count > 3:
            report.add(
                check_name="tautological_tests",
                severity="warning",
                description=f"{tautological_count} trivial assertions found in test files — tests may not verify real behavior",
                affected_files=test_files,
                metric_value=tautological_count,
            )

    def _check_diff_churn(self, report: SlopReport) -> None:
        """Detect high-churn files (many additions AND deletions = rewrite vs surgical fix)."""
        for file_path, file_diff in self.file_diffs.items():
            additions = sum(
                1 for l in file_diff.splitlines()
                if l.startswith("+") and not l.startswith("+++")
            )
            deletions = sum(
                1 for l in file_diff.splitlines()
                if l.startswith("-") and not l.startswith("---")
            )

            total = additions + deletions
            if total > 50 and additions > 20 and deletions > 20:
                report.add(
                    check_name="high_churn",
                    severity="info",
                    description=f"File '{file_path}' has high churn ({additions}+, {deletions}-) — possible rewrite instead of surgical fix",
                    affected_files=[file_path],
                    metric_value=f"+{additions}/-{deletions}",
                )

    def _check_boilerplate_patterns(self, report: SlopReport) -> None:
        """Detect AI boilerplate comment patterns."""
        boilerplate_patterns = [
            (r"# (This|The) (function|method|class) ", "Generic docstring opener"),
            (r"# (Helper|Utility) function to ", "Generic helper comment"),
            (r"// (This|The) function ", "Generic JS comment"),
            (r'""".*This (module|file|class) (provides|contains|implements)', "Generic module docstring"),
            (r"# (TODO|FIXME|HACK|NOTE):.*implement", "TODO without implementation"),
        ]

        boilerplate_count = 0
        for file_path, file_diff in self.file_diffs.items():
            for line in file_diff.splitlines():
                if not line.startswith("+") or line.startswith("+++"):
                    continue
                content = line[1:]
                for pattern, _desc in boilerplate_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        boilerplate_count += 1

        if boilerplate_count > 5:
            report.add(
                check_name="boilerplate_comments",
                severity="warning",
                description=f"{boilerplate_count} AI boilerplate comment patterns detected — possible comment slop",
                metric_value=boilerplate_count,
            )

    def _check_over_engineering(self, report: SlopReport) -> None:
        """Detect signs of over-engineering: unnecessary abstractions."""
        over_eng_patterns = [
            r"class\s+\w+Factory",
            r"class\s+\w+Builder(?!\s*$)",
            r"class\s+\w+Strategy",
            r"class\s+\w+Adapter",
            r"class\s+\w+Decorator",
            r"abstractmethod",
            r"Protocol\[",
        ]

        # Only flag if the issue doesn't mention architecture/design patterns
        issue_mentions_arch = any(
            kw in self.issue_body
            for kw in ["refactor", "architecture", "pattern", "abstract", "design", "interface"]
        )
        if issue_mentions_arch:
            return

        over_eng_count = 0
        for file_path, file_diff in self.file_diffs.items():
            for pattern in over_eng_patterns:
                matches = re.findall(pattern, file_diff)
                over_eng_count += len(matches)

        if over_eng_count > 2:
            report.add(
                check_name="over_engineering",
                severity="warning",
                description=f"{over_eng_count} design pattern abstractions detected — issue doesn't request architectural changes",
                metric_value=over_eng_count,
            )
