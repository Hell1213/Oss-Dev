# OSS Dev Agent Workflow Analysis

## Current Flow

1. **CLI starts** (`cli/oss_commands.py:oss_fix`)
   - Calls `workflow.start(issue_url)` → Sets phase to REPOSITORY_UNDERSTANDING
   - Gets initial phase prompt
   - Creates initial message with phase instructions
   - Starts agent with `agent.run(initial_message)`

2. **Agent runs** (`agent/agent.py:run`)
   - Yields `AGENT_START`
   - Calls `_agentic_loop()` which runs for `max_turns` iterations
   - Each turn:
     - Gets messages from context manager
     - Calls LLM with messages
     - Processes tool calls
     - Adds assistant message to context
     - If no tool calls → returns (exits loop)
     - If tool calls → continues to next turn

3. **Phase Transition** (when agent calls `mark_phase_complete`)
   - Tool executes → calls `workflow.mark_phase_complete()`
   - Phase transitions to next phase
   - Tool result includes new phase prompt
   - Tool result added to context
   - Agent's current turn completes
   - **CLI detects phase transition** and injects new user message

4. **Agent Continues**
   - Next turn picks up injected message
   - Agent sees new phase instructions
   - Agent continues working

## Critical Issues Found

### Issue 1: Agent Loop Exits Early
- Agent loop exits if `not tool_calls` (line 109)
- This is correct - means agent is done responding
- But agent should continue if new messages are added

### Issue 2: Message Injection Timing
- We inject message after phase transition
- But agent's current turn might have already completed
- Next turn should pick it up, but we need to ensure it does

### Issue 3: Agent Might Think Task is Complete
- After completing a phase, agent might think task is done
- Need to ensure agent knows to continue to next phase

## Solution

The current approach of injecting a message should work, but we need to ensure:
1. Agent loop continues after message injection
2. Agent sees the new message in next turn
3. Agent understands it needs to continue working

The agent loop runs for `max_turns` iterations, so as long as we haven't exceeded that, it should continue. The injected message will be picked up in the next turn.

## Verification Checklist

- [ ] Agent receives initial message with Phase 1 instructions
- [ ] Agent completes Phase 1 and calls `mark_phase_complete`
- [ ] Phase transitions to Phase 2
- [ ] CLI injects new message with Phase 2 instructions
- [ ] Agent's next turn picks up Phase 2 message
- [ ] Agent continues working on Phase 2
- [ ] Process repeats for all 7 phases

## Test Plan

1. Start with issue #9
2. Monitor agent behavior through all phases
3. Verify phase transitions work
4. Verify agent continues after each transition
5. Verify all 7 phases complete
6. Verify PR is created
