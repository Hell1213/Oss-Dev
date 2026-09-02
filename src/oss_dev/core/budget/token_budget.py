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
    """Tracks token usage with per-phase and per-session limits."""

    max_total_tokens: int = 500_000
    max_tokens_per_phase: int = 50_000
    max_tokens_per_tool_result: int = 5_000
    spent_total: int = 0
    spent_by_phase: dict[str, int] = field(default_factory=dict)

    def add_usage(self, phase: str | None, tokens: int) -> None:
        self.spent_total += tokens
        if phase:
            self.spent_by_phase[phase] = self.spent_by_phase.get(phase, 0) + tokens
        logger.debug(
            "Token usage: +%d (total: %d, phase '%s': %d)",
            tokens, self.spent_total, phase or "none",
            self.spent_by_phase.get(phase, 0) if phase else 0,
        )

    def can_spend(self, estimated_tokens: int) -> bool:
        if self.spent_total + estimated_tokens > self.max_total_tokens:
            logger.warning(
                "Token budget exceeded: %d + %d > %d",
                self.spent_total, estimated_tokens, self.max_total_tokens,
            )
            return False
        return True

    def phase_budget_remaining(self, phase: str) -> int:
        spent = self.spent_by_phase.get(phase, 0)
        return max(0, self.max_tokens_per_phase - spent)

    def is_phase_over_budget(self, phase: str) -> bool:
        return self.spent_by_phase.get(phase, 0) >= self.max_tokens_per_phase

    def is_session_over_budget(self) -> bool:
        return self.spent_total >= self.max_total_tokens

    def get_summary(self) -> dict[str, int | dict[str, int]]:
        return {
            "spent_total": self.spent_total,
            "budget_total": self.max_total_tokens,
            "remaining": max(0, self.max_total_tokens - self.spent_total),
            "spent_by_phase": dict(self.spent_by_phase),
            "session_over_budget": self.is_session_over_budget(),
        }

    def truncate_tool_result(self, text: str) -> str:
        max_chars = self.max_tokens_per_tool_result * 4
        if len(text) <= max_chars:
            return text
        truncated = text[:max_chars]
        return truncated + "\n\n... (tool result truncated to stay within token budget)"
