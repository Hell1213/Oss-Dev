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

from src.oss_dev.core.state.review_session import SlopIndicator


@dataclass
class SlopReport:
    """Aggregated AI slop detection report."""

    indicators: list[SlopIndicator] = field(default_factory=list)
    slop_score: float = 0.0
    is_likely_slop: bool = False

    def add(self, check_name: str, severity: str, description: str,
            affected_files: list[str] | None = None,
            metric_value: float | int | str | None = None) -> None:
        self.indicators.append(SlopIndicator(
            check_name=check_name, severity=severity, description=description,
            affected_files=affected_files or [], metric_value=metric_value,
        ))


class SlopDetector:
    """Deterministic AI slop detector."""

    def __init__(self, diff_text: str, changed_files: list[str],
                 issue_body: str = "", issue_keywords: list[str] | None = None) -> None:
        self.diff = diff_text
        self.changed_files = changed_files
        self.issue_body = issue_body.lower()
        self.issue_keywords = issue_keywords or self._extract_keywords(issue_body)
        self.file_diffs: dict[str, str] = self._parse_diff(diff_text)

    def _extract_keywords(self, text: str) -> list[str]:
        if not text:
            return []
        stopwords = {"the", "this", "that", "with", "from", "have", "should",
            "would", "could", "there", "their", "where", "which", "when", "what",
            "they", "them", "then", "than", "also", "been", "were", "will", "into",
            "about", "after", "before", "being", "issue", "please", "using", "based"}
        words = re.findall(r"[a-zA-Z_]{5,}", text.lower())
        return [w for w in words if w not in stopwords]

    def _parse_diff(self, diff_text: str) -> dict[str, str]:
        files: dict[str, str] = {}
        current_file = None
        current_lines: list[str] = []
        for line in diff_text.splitlines():
            if line.startswith("diff --git"):
                if current_file:
                    files[current_file] = "\n".join(current_lines)
                match = re.match(r"diff --git a/(.+?) b/(.+)", line)
                current_file = match.group(2) if match else None
                current_lines = [line]
            else:
                current_lines.append(line)
        if current_file:
            files[current_file] = "\n".join(current_lines)
        return files

    def run_all_checks(self) -> SlopReport:
        report = SlopReport()
        self._check_whitespace_only_changes(report)
        self._check_excessive_comments(report)
        self._check_formatting_only_files(report)
        self._check_scope_alignment(report)
        self._check_tautological_tests(report)
        self._check_diff_churn(report)
        self._check_boilerplate_patterns(report)
        self._check_over_engineering(report)
        severity_weights = {"info": 0.1, "warning": 0.3, "critical": 0.6}
        total_weight = sum(severity_weights.get(i.severity, 0.1) for i in report.indicators)
        report.slop_score = min(total_weight, 1.0)
        report.is_likely_slop = report.slop_score >= 0.5
        return report

    def _check_whitespace_only_changes(self, report: SlopReport) -> None:
        for file_path, file_diff in self.file_diffs.items():
            added_lines = [l[1:] for l in file_diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
            if not added_lines:
                continue
            ws_only = all(l.strip() == "" or l.strip().startswith(("import ", "from ", "#")) for l in added_lines)
            if ws_only and added_lines:
                report.add("whitespace_or_import_only", "warning",
                    f"File '{file_path}' has only whitespace/import changes", [file_path], len(added_lines))

    def _check_excessive_comments(self, report: SlopReport) -> None:
        comment_count = 0
        comment_files: list[str] = []
        for file_path, file_diff in self.file_diffs.items():
            file_comments = sum(1 for line in file_diff.splitlines()
                if line.startswith("+") and not line.startswith("+++")
                and (line[1:].strip().startswith("#") or line[1:].strip().startswith("//")))
            if file_comments > 5:
                comment_count += file_comments
                comment_files.append(file_path)
        if comment_count > 10:
            report.add("excessive_comments", "warning",
                f"{comment_count} new comments across {len(comment_files)} files", comment_files, comment_count)

    def _check_formatting_only_files(self, report: SlopReport) -> None:
        for file_path, file_diff in self.file_diffs.items():
            added = [l[1:] for l in file_diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
            removed = [l[1:] for l in file_diff.splitlines() if l.startswith("-") and not l.startswith("---")]
            if not added and not removed:
                continue
            if sorted(l.strip() for l in added) == sorted(l.strip() for l in removed) and len(added) == len(removed) and added != removed:
                report.add("formatting_only", "warning",
                    f"File '{file_path}' has only whitespace formatting changes", [file_path], len(added))

    def _check_scope_alignment(self, report: SlopReport) -> None:
        if not self.issue_keywords:
            return
        unaligned = [f for f in self.changed_files if not any(kw in f.lower() for kw in self.issue_keywords)]
        aligned = [f for f in self.changed_files if f not in unaligned]
        if unaligned and aligned:
            ratio = len(unaligned) / len(self.changed_files)
            if ratio > 0.5:
                report.add("scope_mismatch", "critical",
                    f"{len(unaligned)}/{len(self.changed_files)} files don't match issue keywords", unaligned, f"{ratio:.0%}")

    def _check_tautological_tests(self, report: SlopReport) -> None:
        patterns = [r"assert\s+True", r"assert\s+is\s+not\s+None\s*$", r"assert\s+\w+\s+is\s+not\s+None\s*$", r"pass\s*$"]
        test_files = [f for f in self.changed_files if "test" in f.lower() or f.endswith(("_test.py", ".test.js", ".spec.ts"))]
        if not test_files:
            return
        count = sum(len(re.findall(p, self.file_diffs.get(f, ""), re.MULTILINE)) for f in test_files for p in patterns)
        if count > 3:
            report.add("tautological_tests", "warning",
                f"{count} trivial assertions in test files", test_files, count)

    def _check_diff_churn(self, report: SlopReport) -> None:
        for file_path, file_diff in self.file_diffs.items():
            additions = sum(1 for l in file_diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
            deletions = sum(1 for l in file_diff.splitlines() if l.startswith("-") and not l.startswith("---"))
            if additions + deletions > 50 and additions > 20 and deletions > 20:
                report.add("high_churn", "info",
                    f"File '{file_path}' has high churn ({additions}+, {deletions}-)", [file_path], f"+{additions}/-{deletions}")

    def _check_boilerplate_patterns(self, report: SlopReport) -> None:
        patterns = [r"# (This|The) (function|method|class) ", r"# (Helper|Utility) function to ",
            r"// (This|The) function ", r'""".*This (module|file|class) (provides|contains|implements)',
            r"# (TODO|FIXME|HACK|NOTE):.*implement"]
        count = sum(1 for fd in self.file_diffs.values() for line in fd.splitlines()
            if line.startswith("+") and not line.startswith("+++") and any(re.search(p, line[1:], re.IGNORECASE) for p in patterns))
        if count > 5:
            report.add("boilerplate_comments", "warning", f"{count} AI boilerplate comment patterns", metric_value=count)

    def _check_over_engineering(self, report: SlopReport) -> None:
        if any(kw in self.issue_body for kw in ["refactor", "architecture", "pattern", "abstract", "design", "interface"]):
            return
        patterns = [r"class\s+\w+Factory", r"class\s+\w+Builder(?!\s*$)", r"class\s+\w+Strategy",
            r"class\s+\w+Adapter", r"class\s+\w+Decorator", r"abstractmethod", r"Protocol\["]
        count = sum(len(re.findall(p, fd)) for fd in self.file_diffs.values() for p in patterns)
        if count > 2:
            report.add("over_engineering", "warning",
                f"{count} design pattern abstractions detected", metric_value=count)
