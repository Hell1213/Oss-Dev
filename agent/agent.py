from __future__ import annotations
from typing import AsyncGenerator, Awaitable, Callable
from agent.events import AgentEvent, AgentEventType
from agent.session import Session
from client.response import StreamEventType, TokenUsage, ToolCall, ToolResultMessage, parse_tool_call_arguments
from config.config import Config
from prompts.system import create_loop_breaker_prompt
from tools.base import ToolConfirmation


class Agent:
    def __init__(
        self,
        config: Config,
        confirmation_callback: Callable[[ToolConfirmation], bool] | None = None,
    ):
        self.config = config
        self.session: Session | None = Session(self.config)
        self.session.approval_manager.confirmation_callback = confirmation_callback

    async def run(self, message: str):
        await self.session.hook_system.trigger_before_agent(message)
        yield AgentEvent.agent_start(message)
        self.session.context_manager.add_user_message(message)

        final_response: str | None = None

        async for event in self._agentic_loop():
            yield event

            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")

        await self.session.hook_system.trigger_after_agent(message, final_response)
        yield AgentEvent.agent_end(final_response)

    async def _agentic_loop(self) -> AsyncGenerator[AgentEvent, None]:
        max_turns = self.config.max_turns

        for turn_num in range(max_turns):
            self.session.increment_turn()
            response_text = ""

            # check for context overflow
            if self.session.context_manager.needs_compression():
                summary, usage = await self.session.chat_compactor.compress(
                    self.session.context_manager
                )

                if summary:
                    self.session.context_manager.replace_with_summary(summary)
                    self.session.context_manager.set_latest_usage(usage)
                    self.session.context_manager.add_usage(usage)

            tool_schemas = self.session.tool_registry.get_schemas()

            tool_calls: list[ToolCall] = []
            usage: TokenUsage | None = None

            async for event in self.session.client.chat_completion(
                self.session.context_manager.get_messages(),
                tools=tool_schemas if tool_schemas else None,
            ):
                if event.type == StreamEventType.TEXT_DELTA:
                    if event.text_delta:
                        content = event.text_delta.content
                        response_text += content
                        yield AgentEvent.text_delta(content)
                elif event.type == StreamEventType.TOOL_CALL_START:
                    # Don't emit TOOL_CALL_START during streaming - wait for complete tool call
                    # The complete tool call will be emitted after MESSAGE_COMPLETE
                    # This prevents showing incomplete arguments in CLI
                    pass
                elif event.type == StreamEventType.TOOL_CALL_COMPLETE:
                    if event.tool_call:
                        tool_calls.append(event.tool_call)
                elif event.type == StreamEventType.ERROR:
                    yield AgentEvent.agent_error(
                        event.error or "Unknown error occurred.",
                    )
                elif event.type == StreamEventType.MESSAGE_COMPLETE:
                    usage = event.usage

            # Get the index where we'll add the assistant message
            assistant_message_index = self.session.context_manager.message_count
            
            self.session.context_manager.add_assistant_message(
                response_text or None,
                (
                    [
                        {
                            "id": tc.call_id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": str(tc.arguments),
                            },
                        }
                        for tc in tool_calls
                    ]
                    if tool_calls
                    else None
                ),
            )
            if response_text:
                yield AgentEvent.text_complete(response_text)
                self.session.loop_detector.record_action(
                    "response",
                    text=response_text,
                )

            if not tool_calls:
                if usage:
                    self.session.context_manager.set_latest_usage(usage)
                    self.session.context_manager.add_usage(usage)

                self.session.context_manager.prune_tool_outputs()
                return

            tool_call_results: list[ToolResultMessage] = []
            # Track all tool_call_ids that were added to assistant message
            assistant_tool_call_ids = {tc.call_id for tc in tool_calls}

            for tool_call in tool_calls:
                if not tool_call.name:
                    # Tool call without name - add error result to ensure API protocol is satisfied
                    from tools.base import ToolResult
                    error_result = ToolResult.error_result(
                        error="Tool call missing name",
                        output="",
                    )
                    tool_call_results.append(
                        ToolResultMessage(
                            tool_call_id=tool_call.call_id,
                            content=error_result.to_model_output(),
                            is_error=True,
                        )
                    )
                    continue
                
                # Parse arguments from string to dict
                if isinstance(tool_call.arguments, str):
                    parsed_args = parse_tool_call_arguments(tool_call.arguments)
                else:
                    parsed_args = tool_call.arguments or {}
                
                yield AgentEvent.tool_call_start(
                    tool_call.call_id,
                    tool_call.name,
                    parsed_args,
                )

                self.session.loop_detector.record_action(
                    "tool_call",
                    tool_name=tool_call.name,
                    args=parsed_args,
                )

                try:
                    result = await self.session.tool_registry.invoke(
                        tool_call.name,
                        parsed_args,
                        self.config.cwd,
                        self.session.hook_system,
                        self.session.approval_manager,
                    )
                except Exception as e:
                    # If tool execution fails, add error result to ensure API protocol is satisfied
                    from tools.base import ToolResult
                    result = ToolResult.error_result(
                        error=f"Tool execution failed: {str(e)}",
                        output="",
                    )

                yield AgentEvent.tool_call_complete(
                    tool_call.call_id,
                    tool_call.name,
                    result,
                )

                tool_call_results.append(
                    ToolResultMessage(
                        tool_call_id=tool_call.call_id,
                        content=result.to_model_output(),
                        is_error=not result.success,
                    )
                )

            # Add all tool results to context, inserting them immediately after the assistant message
            # This ensures the API protocol is satisfied: tool results must immediately follow assistant messages with tool_calls
            for tool_result in tool_call_results:
                self.session.context_manager.add_tool_result(
                    tool_result.tool_call_id,
                    tool_result.content,
                    insert_after_assistant_index=assistant_message_index,
                )
            
            # CRITICAL: Validate that every tool_call_id in assistant message has a result
            # This ensures the API protocol is always satisfied
            tool_result_ids = {tr.tool_call_id for tr in tool_call_results}
            missing_ids = assistant_tool_call_ids - tool_result_ids
            if missing_ids:
                # Defensively add error results for any missing IDs, also inserting after assistant message
                from tools.base import ToolResult
                for missing_id in missing_ids:
                    error_result = ToolResult.error_result(
                        error="Tool call was not processed",
                        output="",
                    )
                    self.session.context_manager.add_tool_result(
                        missing_id,
                        error_result.to_model_output(),
                        insert_after_assistant_index=assistant_message_index,
                    )

            loop_detection_error = self.session.loop_detector.check_for_loop()
            if loop_detection_error:
                loop_prompt = create_loop_breaker_prompt(loop_detection_error)
                self.session.context_manager.add_user_message(loop_prompt)

            if usage:
                self.session.context_manager.set_latest_usage(usage)
                self.session.context_manager.add_usage(usage)

            self.session.context_manager.prune_tool_outputs()
        yield AgentEvent.agent_error(f"Maximum turns ({max_turns}) reached")

    async def __aenter__(self) -> Agent:
        await self.session.initialize()
        return self

    async def __aexit__(
        self,
        exc_type,
        exc_val,
        exc_tb,
    ) -> None:
        if self.session and self.session.client and self.session.mcp_manager:
            await self.session.client.close()
            await self.session.mcp_manager.shutdown()
            self.session = None
