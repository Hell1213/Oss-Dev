"""
Workflow Orchestrator Tool

Tool that allows the Agent to interact with the OSS workflow orchestrator.
"""

from pathlib import Path
from tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field

from oss.workflow import OSSWorkflow, WorkflowPhase


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

        try:
            workflow = self._get_workflow(repo_path)

            if params.action == "start":
                if not params.issue_url:
                    return ToolResult.error_result(
                        "issue_url is required for 'start' action"
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
                workflow.mark_phase_complete(current_phase)

                return ToolResult.success_result(
                    f"Phase {current_phase.value} marked complete.\n"
                    f"Transitioned to: {workflow.state.phase.value}\n\n"
                    f"Next: {workflow.get_phase_prompt()}"
                )

            elif params.action == "get_status":
                phase_info = workflow.get_current_phase_info()
                state = workflow.get_state()

                output_lines = [
                    "Workflow Status:",
                    f"  Phase: {phase_info['phase']}",
                    f"  Issue: #{phase_info['issue_number']}" if phase_info.get('issue_number') else "  Issue: None",
                    f"  Branch: {phase_info['branch_name']}" if phase_info.get('branch_name') else "  Branch: Not created",
                    f"  Changes Made: {phase_info['changes_made']}",
                    f"  Tests Passed: {phase_info['tests_passed']}",
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
