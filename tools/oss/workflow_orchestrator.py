"""
Workflow Orchestrator Tool

Tool that allows the Agent to interact with the OSS workflow orchestrator.
"""

from pathlib import Path
import logging
from tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field

from oss.workflow import OSSWorkflow, WorkflowPhase

logger = logging.getLogger(__name__)


class WorkflowOrchestratorParams(BaseModel):
    """Parameters for workflow orchestrator"""

    action: str = Field(
        ...,
        description="Action: 'start', 'resume', 'get_phase_prompt', 'mark_phase_complete', 'get_status'",
    )
    issue_url: str | None = Field(
        None, description="GitHub issue URL (required for 'start' action)"
    )
    path: str | None = Field(
        None,
        description="Path to repository (defaults to current working directory)",
    )


class WorkflowOrchestratorTool(Tool):
    """
    Tool for orchestrating OSS workflow phases.

    This tool allows the Agent to interact with the workflow orchestrator
    to manage phase transitions and get phase-specific guidance.
    """

    name = "workflow_orchestrator"
    description = "Orchestrate OSS contribution workflow phases. Manages state transitions and provides phase-specific guidance."
    kind = ToolKind.READ
    schema = WorkflowOrchestratorParams

    def __init__(self, config):
        """Initialize workflow orchestrator tool."""
        super().__init__(config)
        self._workflows: dict[str, OSSWorkflow] = {}

    def _get_workflow(self, repo_path: Path) -> OSSWorkflow:
        """Get or create workflow for repository."""
        repo_key = str(repo_path.resolve())
        if repo_key not in self._workflows:
            self._workflows[repo_key] = OSSWorkflow(self.config, repo_path)
        return self._workflows[repo_key]

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute workflow orchestrator action"""
        params = WorkflowOrchestratorParams(**invocation.params)
        repo_path = Path(params.path) if params.path else invocation.cwd

        logger.info(f"Workflow orchestrator called: action={params.action}, repo={repo_path}")

        try:
            workflow = self._get_workflow(repo_path)

            if params.action == "start":
                if not params.issue_url:
                    return ToolResult.error_result(
                        "issue_url is required for 'start' action"
                    )
                
                # Check if workflow is already started
                if workflow.state.issue_url and workflow.state.issue_number:
                    return ToolResult.error_result(
                        f"Workflow already started for issue #{workflow.state.issue_number}. "
                        f"Current phase: {workflow.state.phase.value}. "
                        f"Use 'get_status' to check status or 'mark_phase_complete' to continue."
                    )

                # Start workflow (phases 1-2 execute immediately)
                state = await workflow.start(params.issue_url)

                return ToolResult.success_result(
                    f"Workflow started for issue: {params.issue_url}\n"
                    f"Current phase: {state.phase.value}\n"
                    f"Branch: {state.branch_name or 'Not created yet'}\n"
                    f"Issue: #{state.issue_number}\n\n"
                    f"Next: {workflow.get_phase_prompt()}"
                )

            elif params.action == "resume":
                state = await workflow.resume()

                return ToolResult.success_result(
                    f"Workflow resumed\n"
                    f"Current phase: {state.phase.value}\n"
                    f"Branch: {state.branch_name or 'Not created yet'}\n"
                    f"Issue: #{state.issue_number or 'Unknown'}\n\n"
                    f"Continue with: {workflow.get_phase_prompt()}"
                )

            elif params.action == "get_phase_prompt":
                prompt = workflow.get_phase_prompt()
                phase_info = workflow.get_current_phase_info()

                return ToolResult.success_result(
                    f"Current Phase: {phase_info['phase']}\n\n"
                    f"Guidance:\n{prompt}"
                )

            elif params.action == "mark_phase_complete":
                current_phase = workflow.state.phase
                previous_phase = current_phase.value
                
                logger.info(f"Marking phase complete: {previous_phase} (Issue #{workflow.state.issue_number})")
                
                try:
                    await workflow.mark_phase_complete(current_phase)
                except ValueError as e:
                    # Validation failed - return error to agent
                    error_msg = str(e)
                    logger.error(f"Phase completion validation failed: {error_msg}")
                    return ToolResult.error_result(
                        f"❌ Cannot mark phase '{previous_phase}' complete.\n\n"
                        f"{error_msg}\n\n"
                        f"**Action Required:**\n"
                        f"1. Complete the missing work\n"
                        f"2. Verify all requirements are met\n"
                        f"3. Try calling 'mark_phase_complete' again\n\n"
                        f"Use 'workflow_orchestrator(action=\"get_status\")' to check current state."
                    )
                
                new_phase = workflow.state.phase.value
                phase_info = workflow.get_current_phase_info()
                
                logger.info(f"Phase transition successful: {previous_phase} -> {new_phase}")

                # Get the new phase prompt
                new_phase_prompt = workflow.get_phase_prompt()
                
                return ToolResult.success_result(
                    f"✅ Phase '{previous_phase}' marked complete.\n"
                    f"🔄 Transitioned to: {new_phase}\n"
                    f"📋 Issue: #{phase_info.get('issue_number', 'N/A')}\n"
                    f"🌿 Branch: {phase_info.get('branch_name', 'Not created')}\n"
                    f"📝 Changes Made: {'✅ Yes' if phase_info.get('changes_made') else '❌ No'}\n\n"
                    f"=== NEW PHASE: {new_phase.upper()} ===\n"
                    f"{new_phase_prompt}\n\n"
                    f"Continue working on this phase. When complete, call 'mark_phase_complete' again."
                )

            elif params.action == "get_status":
                phase_info = workflow.get_current_phase_info()
                state = workflow.get_state()

                output_lines = [
                    "📋 Workflow Status:",
                    f"  Phase: {phase_info['phase']}",
                    f"  Issue: #{phase_info['issue_number']}" if phase_info.get('issue_number') else "  Issue: None",
                    f"  Branch: {phase_info['branch_name']}" if phase_info.get('branch_name') else "  Branch: Not created",
                    f"  Changes Made: {'✅ Yes' if phase_info['changes_made'] else '❌ No'}",
                    f"  Tests Passed: {'✅ Yes' if phase_info['tests_passed'] else '❌ No'}",
                    f"  PR URL: {phase_info['pr_url']}" if phase_info.get('pr_url') else "  PR: Not created",
                ]

                return ToolResult.success_result("\n".join(output_lines))

            else:
                return ToolResult.error_result(
                    f"Unknown action: {params.action}. "
                    f"Valid actions: start, resume, get_phase_prompt, mark_phase_complete, get_status"
                )

        except ValueError as e:
            return ToolResult.error_result(f"Workflow error: {e}")

        except Exception as e:
            return ToolResult.error_result(f"Failed to execute workflow action: {e}")
