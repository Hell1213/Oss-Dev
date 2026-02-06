"""
Branch Memory Management Tool

Tool for managing branch-level memory, switching branches, and context management.
"""

from pathlib import Path
from tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field


class BranchMemoryParams(BaseModel):
    """Parameters for branch memory operations"""

    action: str = Field(
        ...,
        description="Action: 'switch', 'list', 'summary', 'cleanup', 'get_context'",
    )
    branch_name: str | None = Field(
        None, description="Branch name (required for 'switch', 'summary', 'get_context')"
    )
    days_old: int | None = Field(
        None, description="Days old for cleanup (default: 30)"
    )


class BranchMemoryTool(Tool):
    """
    Tool for managing branch-level memory.

    Supports branch switching, context retrieval, and memory cleanup.
    """

    name = "branch_memory"
    description = "Manage branch-level memory: switch branches, get context summaries, list branches, cleanup old memories."
    kind = ToolKind.READ
    schema = BranchMemoryParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute branch memory action"""
        params = BranchMemoryParams(**invocation.params)
        repo_path = invocation.cwd

        try:
            from oss.memory import BranchMemoryManager

            memory_manager = BranchMemoryManager(repo_path)

            if params.action == "switch":
                if not params.branch_name:
                    return ToolResult.error_result(
                        "branch_name is required for 'switch' action"
                    )

                # Switch to target branch
                target_memory = memory_manager.switch_branch(params.branch_name)

                if target_memory:
                    context_summary = memory_manager.summarize_context(params.branch_name)
                    return ToolResult.success_result(
                        f"Switched to branch: {params.branch_name}\n"
                        f"Context: {context_summary}\n"
                        f"Phase: {target_memory.get('current_phase', 'unknown')}\n"
                        f"Issue: #{target_memory.get('issue_number', 'N/A')}"
                    )
                else:
                    return ToolResult.success_result(
                        f"Switched to branch: {params.branch_name}\n"
                        f"No previous context found. Starting fresh."
                    )

            elif params.action == "list":
                branches = memory_manager.list_branches()

                if not branches:
                    return ToolResult.success_result("No branch memories found.")

                output_lines = ["Branch Memories:"]
                for branch_data in branches:
                    branch_name = branch_data.get("branch_name", "unknown")
                    issue_num = branch_data.get("issue_number")
                    phase = branch_data.get("current_phase", "unknown")
                    status = branch_data.get("status", "unknown")

                    line = f"  {branch_name}"
                    if issue_num:
                        line += f" (Issue #{issue_num})"
                    line += f" - {phase} - {status}"
                    output_lines.append(line)

                return ToolResult.success_result("\n".join(output_lines))

            elif params.action == "summary":
                if not params.branch_name:
                    return ToolResult.error_result(
                        "branch_name is required for 'summary' action"
                    )

                summary = memory_manager.get_branch_summary(params.branch_name)

                if not summary.get("exists"):
                    return ToolResult.error_result(
                        f"No memory found for branch: {params.branch_name}"
                    )

                output_lines = [
                    f"Branch Summary: {summary['branch_name']}",
                    f"  Issue: #{summary['issue_number']}" if summary.get("issue_number") else "  Issue: None",
                    f"  Phase: {summary['current_phase']}",
                    f"  Status: {summary['status']}",
                    f"  Files Modified: {summary['files_modified']}",
                    f"  Completed Steps: {summary['completed_steps']}",
                    f"  Context: {summary['context_summary']}",
                ]

                if summary.get("pr_url"):
                    output_lines.append(f"  PR: {summary['pr_url']}")

                return ToolResult.success_result("\n".join(output_lines))

            elif params.action == "get_context":
                if not params.branch_name:
                    # Get current branch context
                    branch_name = memory_manager.get_current_branch()
                    if not branch_name:
                        return ToolResult.error_result("Not in a git repository")
                else:
                    branch_name = params.branch_name

                memory_data = memory_manager.load_branch(branch_name)
                if not memory_data:
                    return ToolResult.success_result(
                        f"No context found for branch: {branch_name}"
                    )

                context_summary = memory_manager.summarize_context(branch_name)
                return ToolResult.success_result(
                    f"Context for {branch_name}:\n{context_summary}"
                )

            elif params.action == "cleanup":
                days = params.days_old or 30
                cleaned = memory_manager.cleanup_old_memories(days)
                merged_cleaned = memory_manager.cleanup_merged_branches()

                return ToolResult.success_result(
                    f"Cleanup complete.\n"
                    f"  Removed {cleaned} old memories (> {days} days)\n"
                    f"  Removed {merged_cleaned} merged branch memories"
                )

            else:
                return ToolResult.error_result(
                    f"Unknown action: {params.action}. "
                    f"Valid actions: switch, list, summary, get_context, cleanup"
                )

        except Exception as e:
            return ToolResult.error_result(f"Failed to execute branch memory action: {e}")
