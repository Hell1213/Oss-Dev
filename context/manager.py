from datetime import datetime
from typing import Any
from client.response import TokenUsage
from config.config import Config
from prompts.system import get_system_prompt
from dataclasses import dataclass, field

from tools.base import Tool
from utils.text import count_tokens


@dataclass
class MessageItem:
    role: str
    content: str
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    token_count: int | None = None
    pruned_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"role": self.role}

        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id

        if self.tool_calls:
            result["tool_calls"] = self.tool_calls

        # Always include content field - API requires it (use empty string if None)
        result["content"] = self.content if self.content is not None else ""

        return result


class ContextManager:
    PRUNE_PROTECT_TOKENS = 40_000
    PRUNE_MINIMUM_TOKENS = 20_000

    def __init__(
        self,
        config: Config,
        user_memory: str | None,
        tools: list[Tool] | None,
    ) -> None:
        self._system_prompt = get_system_prompt(config, user_memory, tools)
        self.config = config
        self._model_name = self.config.model_name
        self._messages: list[MessageItem] = []
        self._latest_usage = TokenUsage()
        self.total_usage = TokenUsage()

    @property
    def message_count(self) -> int:
        return len(self._messages)

    def add_user_message(self, content: str) -> None:
        item = MessageItem(
            role="user",
            content=content,
            token_count=count_tokens(
                content,
                self._model_name,
            ),
        )

        self._messages.append(item)

    def add_assistant_message(
        self,
        content: str,
        tool_calls: list[dict[str, any]] | None = None,
    ) -> None:
        item = MessageItem(
            role="assistant",
            content=content or "",
            token_count=count_tokens(
                content or "",
                self._model_name,
            ),
            tool_calls=tool_calls or [],
        )

        self._messages.append(item)

    def add_tool_result(self, tool_call_id: str, content: str, insert_after_assistant_index: int | None = None) -> None:
        """
        Add a tool result to the message history.
        
        Args:
            tool_call_id: The ID of the tool call this result corresponds to
            content: The tool result content
            insert_after_assistant_index: If provided, insert immediately after this assistant message index.
                                          This ensures tool results immediately follow assistant messages with tool_calls.
        """
        # Ensure content is never None or empty - API requires a string
        if content is None:
            content = ""
        elif not isinstance(content, str):
            content = str(content)
        
        item = MessageItem(
            role="tool",
            content=content,
            tool_call_id=tool_call_id,
            token_count=count_tokens(content, self._model_name),
        )

        if insert_after_assistant_index is not None:
            # Insert immediately after the assistant message (after any existing tool results for that message)
            insert_pos = insert_after_assistant_index + 1
            # Skip any existing tool results
            while (insert_pos < len(self._messages) and 
                   self._messages[insert_pos].role == "tool"):
                insert_pos += 1
            self._messages.insert(insert_pos, item)
        else:
            # Default: append to end (for backward compatibility)
            self._messages.append(item)

    def _validate_message_history(self) -> None:
        """
        Validate that every assistant message with tool_calls has corresponding tool results
        IMMEDIATELY following it. The API requires this strict ordering.
        Tool results MUST come right after assistant message, before any user messages.
        """
        i = 0
        while i < len(self._messages):
            item = self._messages[i]
            if item.role == "assistant" and item.tool_calls:
                # Collect all tool_call_ids from this assistant message
                tool_call_ids = set()
                for tc in item.tool_calls:
                    if isinstance(tc, dict) and "id" in tc:
                        tool_call_ids.add(tc["id"])
                
                if tool_call_ids:
                    # Check what immediately follows this assistant message
                    found_tool_result_ids = set()
                    j = i + 1
                    # Collect tool results that immediately follow (stop at first non-tool message)
                    while j < len(self._messages) and self._messages[j].role == "tool":
                        tool_result_id = self._messages[j].tool_call_id
                        if tool_result_id:
                            found_tool_result_ids.add(tool_result_id)
                        j += 1
                    
                    # Find missing tool_call_ids
                    missing_ids = tool_call_ids - found_tool_result_ids
                    if missing_ids:
                        # Insert error results IMMEDIATELY after assistant message (before any user messages)
                        # Insert right after the assistant message, before any existing tool results or user messages
                        insert_position = i + 1
                        from tools.base import ToolResult
                        for missing_id in missing_ids:
                            error_result = ToolResult.error_result(
                                error="Tool call was not processed",
                                output="",
                            )
                            error_item = MessageItem(
                                role="tool",
                                content=error_result.to_model_output(),
                                tool_call_id=missing_id,
                                token_count=count_tokens(error_result.to_model_output(), self._model_name),
                            )
                            self._messages.insert(insert_position, error_item)
                            insert_position += 1
                            # Update i to account for inserted item
                            i += 1
            i += 1

    def get_messages(self) -> list[dict[str, Any]]:
        # Validate message history before returning
        self._validate_message_history()
        
        messages = []

        if self._system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": self._system_prompt,
                }
            )

        for item in self._messages:
            messages.append(item.to_dict())

        return messages

    def needs_compression(self) -> bool:
        context_limit = self.config.model.context_window
        current_tokens = self._latest_usage.total_tokens

        return current_tokens > (context_limit * 0.8)

    def set_latest_usage(self, usage: TokenUsage):
        self._latest_usage = usage

    def add_usage(self, usage: TokenUsage):
        self.total_usage += usage

    def replace_with_summary(self, summary: str) -> None:
        self._messages = []

        continuation_content = f"""# Context Restoration (Previous Session Compacted)

        The previous conversation was compacted due to context length limits. Below is a detailed summary of the work done so far. 

        **CRITICAL: Actions listed under "COMPLETED ACTIONS" are already done. DO NOT repeat them.**

        ---

        {summary}

        ---

        Resume work from where we left off. Focus ONLY on the remaining tasks."""

        summary_item = MessageItem(
            role="user",
            content=continuation_content,
            token_count=count_tokens(continuation_content, self._model_name),
        )
        self._messages.append(summary_item)

        ack_content = """I've reviewed the context from the previous session. I understand:
- The original goal and what was requested
- Which actions are ALREADY COMPLETED (I will NOT repeat these)
- The current state of the project
- What still needs to be done

I'll continue with the REMAINING tasks only, starting from where we left off."""
        ack_item = MessageItem(
            role="assistant",
            content=ack_content,
            token_count=count_tokens(ack_content, self._model_name),
        )
        self._messages.append(ack_item)

        continue_content = (
            "Continue with the REMAINING work only. Do NOT repeat any completed actions. "
            "Proceed with the next step as described in the context above."
        )

        continue_item = MessageItem(
            role="user",
            content=continue_content,
            token_count=count_tokens(continue_content, self._model_name),
        )
        self._messages.append(continue_item)

    def prune_tool_outputs(self) -> int:
        user_message_count = sum(1 for msg in self._messages if msg.role == "user")

        if user_message_count < 2:
            return 0

        total_tokens = 0
        pruned_tokens = 0
        to_prune: list[MessageItem] = []

        for msg in reversed(self._messages):
            if msg.role == "tool" and msg.tool_call_id:
                if msg.pruned_at:
                    break

                tokens = msg.token_count or count_tokens(msg.content, self._model_name)
                total_tokens += tokens

                if total_tokens > self.PRUNE_PROTECT_TOKENS:
                    pruned_tokens += tokens
                    to_prune.append(msg)

        if pruned_tokens < self.PRUNE_MINIMUM_TOKENS:
            return 0

        pruned_count = 0

        for msg in to_prune:
            msg.content = "[Old tool result content cleared]"
            msg.token_count = count_tokens(msg.content, self._model_name)
            msg.pruned_at = datetime.now()
            pruned_count += 1

        return pruned_count

    def clear(self) -> None:
        self._messages = []
