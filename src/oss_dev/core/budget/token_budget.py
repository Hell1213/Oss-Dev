"""Token Budget System — tracks and limits token usage per session.

Prevents runaway token consumption on complex issues by enforcing
per-phase and per-session token limits.

Usage:
    from src.oss_dev.core.budget.token_budget import TokenBudget

    budget = TokenBudget(max_total=500_000, max_per_phase=50_000)
    budget.add_usage(phase="implementation", tokens=5000)
    if not budget.can_spend(estimated=3000):
        # Force compaction or wrap up
        ...
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TokenBudget:
    """Tracks token usage with per-phase and per-session limits.

    Attributes:
        max_total_tokens: Maximum tokens for the entire session.
        max_tokens_per_phase: Maximum tokens per workflow phase.
        max_tokens_per_tool_result: Cap for individual tool result truncation.
        spent_total: Total tokens spent so far.
        spent_by_phase: Token usage tracked per phase.
    """

    max_total_tokens: int = 500_000
    max_tokens_per_phase: int = 50_000
    max_tokens_per_tool_result: int = 5_000
    spent_total: int = 0
    spent_by_phase: dict[str, int] = field(default_factory=dict)

    def add_usage(self, phase: str | None, tokens: int) -> None:
        """Record token usage.

        Args:
            phase: Current workflow phase (or None for non-workflow usage).
            tokens: Number of tokens consumed.
        """
        self.spent_total += tokens
        if phase:
            self.spent_by_phase[phase] = self.spent_by_phase.get(phase, 0) + tokens
        logger.debug(
            "Token usage: +%d (total: %d, phase '%s': %d)",
            tokens, self.spent_total, phase or "none",
            self.spent_by_phase.get(phase, 0) if phase else 0,
        )

    def can_spend(self, estimated_tokens: int) -> bool:
        """Check if we can afford to spend estimated_tokens.

        Args:
            estimated_tokens: Estimated tokens for the next operation.

        Returns:
            True if within budget, False if budget would be exceeded.
        """
        if self.spent_total + estimated_tokens > self.max_total_tokens:
            logger.warning(
                "Token budget exceeded: %d + %d > %d",
                self.spent_total, estimated_tokens, self.max_total_tokens,
            )
            return False
        return True

    def phase_budget_remaining(self, phase: str) -> int:
        """How many tokens are left in the current phase budget.

        Args:
            phase: Workflow phase name.

        Returns:
            Remaining tokens for this phase.
        """
        spent = self.spent_by_phase.get(phase, 0)
        return max(0, self.max_tokens_per_phase - spent)

    def is_phase_over_budget(self, phase: str) -> bool:
        """Check if a phase has exceeded its token budget.

        Args:
            phase: Workflow phase name.

        Returns:
            True if the phase is over budget.
        """
        return self.spent_by_phase.get(phase, 0) >= self.max_tokens_per_phase

    def is_session_over_budget(self) -> bool:
        """Check if the total session has exceeded its token budget.

        Returns:
            True if the session is over budget.
        """
        return self.spent_total >= self.max_total_tokens

    def get_summary(self) -> dict[str, int | dict[str, int]]:
        """Get a summary of token usage.

        Returns:
            Dict with total spent, budget remaining, and per-phase breakdown.
        """
        return {
            "spent_total": self.spent_total,
            "budget_total": self.max_total_tokens,
            "remaining": max(0, self.max_total_tokens - self.spent_total),
            "spent_by_phase": dict(self.spent_by_phase),
            "session_over_budget": self.is_session_over_budget(),
        }

    def truncate_tool_result(self, text: str) -> str:
        """Truncate a tool result to stay within per-result token budget.

        Uses a rough 4-chars-per-token heuristic.

        Args:
            text: Tool result text.

        Returns:
            Truncated text (with note if truncated).
        """
        # Rough estimate: 4 chars per token
        max_chars = self.max_tokens_per_tool_result * 4
        if len(text) <= max_chars:
            return text

        truncated = text[:max_chars]
        return truncated + "\n\n... (tool result truncated to stay within token budget)"
