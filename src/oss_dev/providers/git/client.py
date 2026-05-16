"""Git provider implementation.

Wraps git CLI operations in a clean async-safe interface.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from oss_dev.core.contracts.provider import Commit, GitProvider, GitStatus
from oss_dev.core.errors import ProviderError


class GitCLIProvider(GitProvider):
    """Git provider using the git CLI."""

    def __init__(self, repo_path: Path) -> None:
        self._repo_path = repo_path.resolve()

    def _run(self, args: list[str]) -> str:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise ProviderError(
                f"Git error: {e.stderr.strip()}",
                details={"args": args, "cwd": str(self._repo_path)},
            ) from e

    def _run_no_check(self, args: list[str]) -> tuple[int, str, str]:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except FileNotFoundError as e:
            raise ProviderError("Git is not installed") from e

    async def current_branch(self) -> str:
        return self._run(["rev-parse", "--abbrev-ref", "HEAD"])

    async def create_branch(self, name: str, base: str = "main") -> None:
        self._run(["checkout", "-b", name, base])

    async def checkout(self, branch: str) -> None:
        self._run(["checkout", branch])

    async def commit(self, message: str, files: Optional[list[str]] = None) -> str:
        if files:
            self._run(["add", *files])
        else:
            self._run(["add", "-A"])
        self._run(["commit", "-m", message])
        return self._run(["rev-parse", "HEAD"])

    async def push(self, remote: str = "origin", branch: Optional[str] = None) -> None:
        if branch:
            self._run(["push", remote, branch])
        else:
            branch = await self.current_branch()
            rc, stdout, stderr = self._run_no_check(["push", remote, branch])
            if rc != 0 and "has no upstream" in stderr:
                self._run(["push", "-u", remote, branch])

    async def diff(
        self, base: Optional[str] = None, head: Optional[str] = None
    ) -> str:
        if base and head:
            return self._run(["diff", base, head])
        return self._run(["diff"])

    async def status(self) -> GitStatus:
        branch = await self.current_branch()
        staged: list[str] = []
        unstaged: list[str] = []
        untracked: list[str] = []
        porcelain = self._run(["status", "--porcelain"])
        for line in porcelain.split("\n"):
            if not line.strip():
                continue
            if line.startswith("??"):
                untracked.append(line[3:])
            elif line.startswith(" "):
                unstaged.append(line[3:])
            else:
                staged.append(line[3:])
        ahead = behind = 0
        rc, stdout, _ = self._run_no_check(
            ["rev-list", "--left-right", "--count", "HEAD...@{upstream}"]
        )
        if rc == 0 and stdout:
            parts = stdout.split()
            if len(parts) == 2:
                ahead, behind = int(parts[0]), int(parts[1])
        return GitStatus(
            branch=branch,
            staged=staged,
            unstaged=unstaged,
            untracked=untracked,
            ahead=ahead,
            behind=behind,
        )

    async def log(self, max_count: int = 10) -> list[Commit]:
        output = self._run(
            [
                "log",
                f"--max-count={max_count}",
                "--format=%H|||%s|||%an|||%ai",
            ]
        )
        commits = []
        for line in output.split("\n"):
            if not line.strip():
                continue
            parts = line.split("|||")
            if len(parts) >= 4:
                commits.append(
                    Commit(
                        hash=parts[0],
                        message=parts[1],
                        author=parts[2],
                        timestamp=parts[3],
                    )
                )
        return commits
