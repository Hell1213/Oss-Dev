"""
OSS Dev Agent CLI Commands

Click command group for OSS-specific commands.
"""

import asyncio
import subprocess
import logging
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.text import Text
from rich import box
from rich.align import Align
from rich.spinner import Spinner
from rich.live import Live
from rich.status import Status

console = Console()
logger = logging.getLogger(__name__)


def validate_oss_enabled(config) -> bool:
    """Check if OSS is enabled in config."""
    if not config.oss.enabled:
        console.print(
            "[error]OSS Dev Agent is not enabled.[/error]\n"
            "Set 'oss.enabled = true' in your config file or set GITHUB_TOKEN environment variable."
        )
        return False
    
    # Check for GitHub token
    if not config.github_token:
        console.print(
            "[error]GitHub token not found.[/error]\n"
            "Set GITHUB_TOKEN environment variable or add 'github_token' to [oss] section in config."
        )
        return False
    
    return True


def get_repo_from_cwd(cwd: Path) -> Optional[tuple[str, str]]:
    """
    Get repository owner and name from current directory.

    Returns:
        Tuple of (owner, repo) or None
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip()
        if "github.com" in url:
            parts = url.replace(".git", "").split("github.com/")[-1].split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]
    except Exception:
        pass
    return None


@click.group(name="oss-dev", help="OSS Dev Agent - Work on GitHub issues")
@click.option(
    "--cwd",
    "-c",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Working directory (default: current directory)",
)
@click.pass_context
def oss_dev_group(ctx: click.Context, cwd: Optional[Path]):
    """OSS Dev Agent command group."""
    ctx.ensure_object(dict)
    
    # Import here to avoid circular imports
    from config.config import Config
    from config.loader import load_config
    
    # Load config
    try:
        config = load_config(cwd=cwd)
        ctx.obj["config"] = config
        ctx.obj["cwd"] = cwd or config.cwd
    except Exception as e:
        console.print(f"[error]Configuration Error: {e}[/error]")
        ctx.exit(1)
    
    errors = config.validate()
    if errors:
        for error in errors:
            console.print(f"[error]{error}[/error]")
        ctx.exit(1)


@oss_dev_group.command(name="fix", help="Start working on a GitHub issue")
@click.argument("issue_url", required=True)
@click.pass_context
def oss_fix(ctx: click.Context, issue_url: str):
    """Start working on a GitHub issue from scratch."""
    from config.config import Config
    from oss.workflow import OSSWorkflow
    from agent.agent import Agent
    from agent.events import AgentEventType
    
    config: Config = ctx.obj["config"]
    cwd: Path = ctx.obj["cwd"]
    
    if not validate_oss_enabled(config):
        ctx.exit(1)
    
    async def run_fix():
        # Beautiful welcome banner
        welcome_text = Text()
        welcome_text.append("🚀 ", style="cyan")
        welcome_text.append("OSS Dev Agent", style="bold cyan")
        welcome_text.append(" - Starting workflow", style="cyan")
        
        welcome_panel = Panel(
            Text(f"Issue: {issue_url}", style="white"),
            title=welcome_text,
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
        console.print()
        console.print(welcome_panel)
        console.print()
        
        workflow = OSSWorkflow(config, repository_path=cwd)
        
        try:
            # Start workflow (phases 1-2 execute immediately)
            state = await workflow.start(issue_url)
            
            # Display initial workflow status with beautiful formatting
            status_table = Table.grid(padding=(0, 2))
            status_table.add_column(style="cyan bold", justify="right")
            status_table.add_column(style="white")
            
            status_table.add_row("Phase:", f"[yellow]{state.phase.value.replace('_', ' ').title()}[/yellow]")
            status_table.add_row("Issue:", f"[bold]#{state.issue_number}[/bold]")
            if state.branch_name:
                status_table.add_row("Branch:", f"[green]{state.branch_name}[/green]")
            
            status_panel = Panel(
                status_table,
                title="[bold cyan]📋 Workflow Status[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(1, 2),
            )
            console.print()
            console.print(status_panel)
            console.print()
            
            # Get phase prompt for Agent
            phase_prompt = workflow.get_phase_prompt()
            
            # Create initial message for Agent
            initial_message = f"""I'm working on GitHub issue: {issue_url}

Current workflow phase: {state.phase.value}

{phase_prompt}

## IMPORTANT: Phase Completion
After completing each phase, you MUST call the 'workflow_orchestrator' tool with action 'mark_phase_complete' to transition to the next phase.

Example:
- After completing planning: workflow_orchestrator(action='mark_phase_complete')
- After completing implementation: workflow_orchestrator(action='mark_phase_complete')
- After completing verification: workflow_orchestrator(action='mark_phase_complete')
- And so on for each phase...

The workflow will automatically transition to the next phase when you mark the current one complete.

Use 'workflow_orchestrator' tool with action 'get_status' to check current workflow state at any time."""
            
            # Track current phase for display
            current_phase_display = state.phase.value.replace("_", " ").title()
            last_tool_name = None
            tool_call_count = 0
            status = None
            
            # Run Agent with workflow guidance
            async with Agent(config) as agent:
                # Show initial phase
                console.print(f"\n[bold cyan]📋 Phase: {current_phase_display}[/bold cyan]\n")
                
                # Use try/finally to ensure async generator is properly closed
                event_stream = agent.run(initial_message)
                try:
                    async for event in event_stream:
                        if event.type == AgentEventType.TEXT_DELTA:
                            # Suppress verbose LLM output - only log to debug
                            logger.debug(f"LLM text delta: {event.data.get('content', '')[:50]}...")
                            # Don't print to console - too verbose
                            pass
                        elif event.type == AgentEventType.TEXT_COMPLETE:
                            # Suppress verbose LLM output
                            logger.debug(f"LLM text complete")
                            # Don't print to console - too verbose
                            pass
                        elif event.type == AgentEventType.TOOL_CALL_START:
                            tool_name = event.data.get("name", "unknown")
                            tool_args = event.data.get("arguments", {})
                            
                            # Log tool call
                            logger.debug(f"Tool call started: {tool_name} with args: {tool_args}")
                            
                            # Special handling for workflow_orchestrator to show phase transitions
                            if tool_name == "workflow_orchestrator":
                                action = tool_args.get("action", "unknown") if isinstance(tool_args, dict) else "unknown"
                                if action == "mark_phase_complete":
                                    # Show phase completion
                                    console.print(f"\n[green]✓[/green] [bold]Phase Complete:[/bold] {current_phase_display}")
                                elif action == "get_status":
                                    # Silent - just checking status
                                    pass
                                else:
                                    logger.info(f"Workflow orchestrator called: action={action}")
                            else:
                                # Only show tool name if it's different from last one (avoid spam)
                                if tool_name != last_tool_name:
                                    tool_call_count += 1
                                    # Show tool name but keep it minimal
                                    if tool_call_count <= 3 or tool_name in ["git_branch", "git_commit", "git_push", "create_pr", "create_start_here"]:
                                        console.print(f"[dim]→ {tool_name}[/dim]")
                                    last_tool_name = tool_name
                        elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                            tool_name = event.data.get("name", "unknown")
                            result = event.data.get("output", "")
                            success = event.data.get("success", False)
                            
                            # Log tool completion
                            logger.debug(f"Tool call completed: {tool_name}, success={success}")
                            
                            # Reset last tool name for next iteration
                            if tool_name == last_tool_name:
                                last_tool_name = None
                            
                            # Handle user confirmation requests
                            if tool_name == "user_confirm" and "CONFIRMATION_REQUIRED" in result:
                                # Extract confirmation message
                                lines = result.split("\n")
                                confirm_msg = ""
                                default_yes = True
                                for line in lines:
                                    if line.startswith("CONFIRMATION_REQUIRED:"):
                                        confirm_msg = line.replace("CONFIRMATION_REQUIRED:", "").strip()
                                    elif "Default:" in line:
                                        default_yes = "yes" in line.lower()
                                
                                # Ask user for confirmation with beautiful formatting
                                confirm_panel = Panel(
                                    Text(confirm_msg, style="yellow"),
                                    title="[bold yellow]❓ Confirmation Required[/bold yellow]",
                                    border_style="yellow",
                                    box=box.ROUNDED,
                                    padding=(1, 2),
                                )
                                console.print()
                                console.print(confirm_panel)
                                console.print()
                                
                                response = click.confirm("[bold]Proceed?[/bold]", default=default_yes)
                                
                                if response:
                                    success_panel = Panel(
                                        Text("User confirmed. Proceeding with push and PR creation...", style="green"),
                                        border_style="green",
                                        box=box.ROUNDED,
                                        padding=(1, 2),
                                    )
                                    console.print()
                                    console.print(success_panel)
                                    console.print()
                                    
                                    # Inject confirmation result back to agent
                                    # NOTE: add_tool_result is NOT async, so no await needed
                                    if agent and agent.session and agent.session.context_manager:
                                        agent.session.context_manager.add_tool_result(
                                            event.data.get("call_id", ""),
                                            "User confirmed: YES. Proceed with push and PR creation."
                                        )
                                else:
                                    branch_name = workflow.state.branch_name or "your-branch"
                                    decline_content = Text()
                                    decline_content.append("User declined. Skipping push and PR creation.\n\n", style="yellow")
                                    decline_content.append("To push manually:\n", style="dim")
                                    decline_content.append(f"  git push -u origin {branch_name}", style="cyan")
                                    
                                    decline_panel = Panel(
                                        decline_content,
                                        title="[bold yellow]✗ Action Declined[/bold yellow]",
                                        border_style="yellow",
                                        box=box.ROUNDED,
                                        padding=(1, 2),
                                    )
                                    console.print()
                                    console.print(decline_panel)
                                    console.print()
                                    
                                    # Inject decline result back to agent
                                    # NOTE: add_tool_result is NOT async, so no await needed
                                    if agent and agent.session and agent.session.context_manager:
                                        agent.session.context_manager.add_tool_result(
                                            event.data.get("call_id", ""),
                                            "User declined: NO. Skip push and PR creation. Show manual instructions instead."
                                        )
                                continue
                            
                            # Show phase transitions prominently with beautiful formatting
                            if tool_name == "workflow_orchestrator" and success:
                                if "Transitioned to:" in result or "marked complete" in result.lower():
                                    # Extract new phase
                                    new_phase = None
                                    if "Transitioned to:" in result:
                                        for line in result.split("\n"):
                                            if "Transitioned to:" in line:
                                                new_phase = line.split("Transitioned to:")[-1].strip()
                                                break
                                    
                                    if new_phase:
                                        current_phase_display = new_phase.replace("_", " ").title()
                                        # Show new phase
                                        console.print(f"\n[bold cyan]→ Next Phase: {current_phase_display}[/bold cyan]\n")
                                        logger.info(f"Phase transition: {new_phase}")
                                        # Reset tool call counter for new phase
                                        tool_call_count = 0
                                        last_tool_name = None
                                        
                                        # Get updated phase prompt and inject it as a new message to continue
                                        # CRITICAL: This ensures agent continues working after phase transition
                                        try:
                                            new_phase_prompt = workflow.get_phase_prompt()
                                            continue_message = f"""✅ Phase transition complete! 

🔄 **NEW PHASE: {new_phase.replace('_', ' ').upper()}**

{new_phase_prompt}

**IMPORTANT:** You MUST continue working on this phase. This is NOT the end of the workflow. Complete all required tasks for this phase, then call 'workflow_orchestrator(action='mark_phase_complete')' to proceed to the next phase.

The workflow has {7 - ['repository_understanding', 'issue_intake', 'planning', 'implementation', 'verification', 'validation', 'commit_and_pr'].index(new_phase)} phases remaining. Keep working!"""
                                            # Inject message to continue workflow - agent's next turn will pick this up
                                            # NOTE: add_user_message is NOT async, so no await needed
                                            if agent and agent.session and agent.session.context_manager:
                                                agent.session.context_manager.add_user_message(continue_message)
                                                logger.info(f"✅ Injected continue message for phase: {new_phase}")
                                            else:
                                                logger.warning("Agent session not available for message injection")
                                            # Show user that agent will continue
                                            console.print(f"[dim]→ Agent will continue with {current_phase_display}...[/dim]")
                                        except Exception as e:
                                            logger.error(f"❌ Could not inject continue message: {e}")
                                            console.print(f"[error]Warning: Could not inject continue message. Agent may stop.[/error]")
                            else:
                                # Minimal tool complete indicator - only for important tools
                                if tool_name in ["git_branch", "git_commit", "git_push", "create_pr", "create_start_here"]:
                                    if success:
                                        console.print(f"[green]✓[/green] [dim]{tool_name} completed[/dim]")
                                    else:
                                        console.print(f"[red]✗[/red] [dim]{tool_name} failed[/dim]")
                        elif event.type == AgentEventType.AGENT_ERROR:
                            console.print(f"\n[error]{event.data.get('error', 'Unknown error')}[/error]")
                finally:
                    # Properly close the async generator to prevent "Task destroyed" warnings
                    if event_stream is not None:
                        try:
                            # Close the async generator properly
                            await event_stream.aclose()
                        except (GeneratorExit, StopAsyncIteration):
                            # These are expected when closing generators
                            pass
                        except Exception as e:
                            logger.debug(f"Error closing event stream: {e}")
            
        except ValueError as e:
            console.print(f"[error]Invalid issue URL: {e}[/error]")
            ctx.exit(1)
        except Exception as e:
            console.print(f"[error]Failed to start OSS workflow: {e}[/error]")
            ctx.exit(1)
    
    # Run async function - use new event loop
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_fix())
    finally:
        loop.close()


@oss_dev_group.command(name="review", help="Work on an issue in the current repository")
@click.argument("issue_number", type=int, required=True)
@click.pass_context
def oss_review(ctx: click.Context, issue_number: int):
    """Work on an issue when already in the repository."""
    from config.config import Config
    from oss.workflow import OSSWorkflow
    from oss.memory import BranchMemoryManager
    from agent.agent import Agent
    from agent.events import AgentEventType
    
    config: Config = ctx.obj["config"]
    cwd: Path = ctx.obj["cwd"]
    
    if not validate_oss_enabled(config):
        ctx.exit(1)
    
    # Get repo from current directory
    repo_info = get_repo_from_cwd(cwd)
    if not repo_info:
        console.print(
            "[error]Could not determine repository.[/error]\n"
            "Make sure you're in a git repository with a GitHub remote, "
            "or use 'oss-dev fix <full_issue_url>' instead."
        )
        ctx.exit(1)
    
    owner, repo = repo_info
    issue_url = f"https://github.com/{owner}/{repo}/issues/{issue_number}"
    
    # Check if branch already exists for this issue
    memory_manager = BranchMemoryManager(cwd)
    branches = memory_manager.list_branches()
    existing_branch = None
    
    for branch_data in branches:
        if branch_data.get("issue_number") == issue_number:
            existing_branch = branch_data.get("branch_name")
            break
    
    if existing_branch:
        console.print(
            f"[info]Found existing branch: {existing_branch}[/info]\n"
            f"Use 'oss-dev switch {existing_branch}' to resume work on this branch."
        )
        ctx.exit(0)
    
    # Start new workflow
    async def run_review():
        console.print(f"[bold]Starting OSS workflow for issue #{issue_number}[/bold]")
        console.print(f"[dim]Repository: {owner}/{repo}[/dim]")
        
        workflow = OSSWorkflow(config, repository_path=cwd)
        
        try:
            state = await workflow.start(issue_url)
            phase_prompt = workflow.get_phase_prompt()
            
            initial_message = f"""I'm working on GitHub issue: {issue_url}

Current workflow phase: {state.phase.value}

{phase_prompt}

Please use the 'workflow_orchestrator' tool to manage the workflow and proceed through the phases."""
            
            async with Agent(config) as agent:
                async for event in agent.run(initial_message):
                    if event.type == AgentEventType.TEXT_DELTA:
                        console.print(event.data.get("content", ""), end="")
                    elif event.type == AgentEventType.TEXT_COMPLETE:
                        console.print(event.data.get("content", ""))
                    elif event.type == AgentEventType.TOOL_CALL_START:
                        tool_name = event.data.get("name", "unknown")
                        console.print(f"\n[dim]🔧 Using tool: {tool_name}[/dim]")
                    elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                        console.print("[dim]Tool complete[/dim]")
                    elif event.type == AgentEventType.AGENT_ERROR:
                        console.print(f"\n[error]{event.data.get('error', 'Unknown error')}[/error]")
        
        except Exception as e:
            console.print(f"[error]Failed to start OSS workflow: {e}[/error]")
            ctx.exit(1)
    
    # Run async function
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_review())
    finally:
        loop.close()


@oss_dev_group.command(name="resume", help="Continue work on current branch")
@click.pass_context
def oss_resume(ctx: click.Context):
    """Continue work on current branch."""
    from config.config import Config
    from oss.workflow import OSSWorkflow
    from agent.agent import Agent
    from agent.events import AgentEventType
    
    config: Config = ctx.obj["config"]
    cwd: Path = ctx.obj["cwd"]
    
    if not validate_oss_enabled(config):
        ctx.exit(1)
    
    async def run_resume():
        workflow = OSSWorkflow(config, repository_path=cwd)
        
        try:
            state = await workflow.resume()
            
            if not state.issue_url:
                console.print(
                    "[error]No workflow found for current branch.[/error]\n"
                    "Use 'oss-dev fix <issue_url>' or 'oss-dev review <issue_number>' to start."
                )
                ctx.exit(1)
            
            phase_prompt = workflow.get_phase_prompt()
            
            initial_message = f"""Resuming OSS workflow.

Current phase: {state.phase.value}
Issue: #{state.issue_number or 'Unknown'}
Branch: {state.branch_name or 'Not created'}

{phase_prompt}

Continue from where we left off."""
            
            console.print(f"[bold]Resuming workflow on branch: {state.branch_name or 'unknown'}[/bold]")
            console.print(f"[dim]Issue: #{state.issue_number} | Phase: {state.phase.value}[/dim]\n")
            
            async with Agent(config) as agent:
                async for event in agent.run(initial_message):
                    if event.type == AgentEventType.TEXT_DELTA:
                        console.print(event.data.get("content", ""), end="")
                    elif event.type == AgentEventType.TEXT_COMPLETE:
                        console.print(event.data.get("content", ""))
                    elif event.type == AgentEventType.TOOL_CALL_START:
                        tool_name = event.data.get("name", "unknown")
                        console.print(f"\n[dim]🔧 Using tool: {tool_name}[/dim]")
                    elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                        console.print("[dim]Tool complete[/dim]")
                    elif event.type == AgentEventType.AGENT_ERROR:
                        console.print(f"\n[error]{event.data.get('error', 'Unknown error')}[/error]")
        
        except Exception as e:
            console.print(f"[error]Failed to resume workflow: {e}[/error]")
            ctx.exit(1)
    
    # Run async function
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_resume())
    finally:
        loop.close()


@oss_dev_group.command(name="status", help="Show current work status")
@click.pass_context
def oss_status(ctx: click.Context):
    """Show current work status."""
    from config.config import Config
    from oss.workflow import OSSWorkflow
    from oss.memory import BranchMemoryManager
    
    config: Config = ctx.obj["config"]
    cwd: Path = ctx.obj["cwd"]
    
    if not validate_oss_enabled(config):
        ctx.exit(1)
    
    workflow = OSSWorkflow(config, repository_path=cwd)
    phase_info = workflow.get_current_phase_info()
    memory_manager = BranchMemoryManager(cwd)
    
    # Get current branch
    current_branch = memory_manager.get_current_branch()
    
    # Beautiful status display
    status_table = Table.grid(padding=(0, 2))
    status_table.add_column(style="cyan bold", justify="right", width=15)
    status_table.add_column(style="white")
    
    if current_branch:
        status_table.add_row("Branch:", f"[green]{current_branch}[/green]")
    else:
        status_table.add_row("Branch:", "[dim]Not in a git repository[/dim]")
    
    if phase_info.get('issue_number'):
        status_table.add_row("Issue:", f"[bold]#{phase_info['issue_number']}[/bold]")
        if phase_info.get('issue_url'):
            status_table.add_row("URL:", f"[dim]{phase_info['issue_url']}[/dim]")
    
    status_table.add_row("Phase:", f"[yellow]{phase_info['phase'].replace('_', ' ').title()}[/yellow]")
    status_table.add_row("Changes:", "[green]✓ Yes[/green]" if phase_info.get('changes_made') else "[dim]No[/dim]")
    status_table.add_row("Tests:", "[green]✓ Passed[/green]" if phase_info.get('tests_passed') else "[dim]Not run[/dim]")
    
    if phase_info.get('pr_url'):
        status_table.add_row("PR:", f"[cyan]{phase_info['pr_url']}[/cyan]")
    
    status_panel = Panel(
        status_table,
        title="[bold cyan]📋 OSS Workflow Status[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print()
    console.print(status_panel)
    
    # Get branch summary if available
    if current_branch:
        summary = memory_manager.get_branch_summary(current_branch)
        if summary.get("exists"):
            summary_table = Table.grid(padding=(0, 2))
            summary_table.add_column(style="cyan bold", justify="right", width=15)
            summary_table.add_column(style="white")
            
            if summary.get("context_summary"):
                summary_table.add_row("Context:", f"[dim]{summary['context_summary']}[/dim]")
            if summary.get("files_modified", 0) > 0:
                summary_table.add_row("Files Modified:", f"[green]{summary['files_modified']}[/green]")
            
            if summary_table.rows:
                summary_panel = Panel(
                    summary_table,
                    title="[bold]Branch Summary[/bold]",
                    border_style="dim",
                    box=box.ROUNDED,
                    padding=(1, 2),
                )
                console.print()
                console.print(summary_panel)
    
    # Show git status if in repo
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        if result.stdout.strip():
            changes_panel = Panel(
                result.stdout,
                title="[bold]Uncommitted Changes[/bold]",
                border_style="yellow",
                box=box.ROUNDED,
                padding=(1, 2),
            )
            console.print()
            console.print(changes_panel)
    except Exception:
        pass
    
    console.print()


@oss_dev_group.command(name="list", help="List active branches with issues")
@click.pass_context
def oss_list(ctx: click.Context):
    """List active branches with issues."""
    from config.config import Config
    from oss.memory import BranchMemoryManager
    
    config: Config = ctx.obj["config"]
    cwd: Path = ctx.obj["cwd"]
    
    if not validate_oss_enabled(config):
        ctx.exit(1)
    
    memory_manager = BranchMemoryManager(cwd)
    branches = memory_manager.list_branches()
    
    if not branches:
        console.print("[dim]No active branches found.[/dim]")
        return
    
    console.print("\n[bold]Active Branches[/bold]")
    console.print("─" * 70)
    
    current_branch = memory_manager.get_current_branch()
    
    for branch_data in branches:
        branch_name = branch_data.get("branch_name", "unknown")
        issue_num = branch_data.get("issue_number")
        phase = branch_data.get("current_phase", "unknown")
        status = branch_data.get("status", "unknown")
        pr_url = branch_data.get("pr_url")
        
        # Highlight current branch
        if branch_name == current_branch:
            branch_display = f"[bold cyan]* {branch_name}[/bold cyan]"
        else:
            branch_display = f"  {branch_name}"
        
        console.print(branch_display)
        
        if issue_num:
            console.print(f"    Issue: [cyan]#{issue_num}[/cyan]")
        console.print(f"    Phase: [yellow]{phase}[/yellow] | Status: {status}")
        
        if pr_url:
            console.print(f"    PR: [cyan]{pr_url}[/cyan]")
        
        # Show context summary if available
        summary = memory_manager.get_branch_summary(branch_name)
        if summary.get("context_summary"):
            console.print(f"    Context: [dim]{summary['context_summary'][:60]}...[/dim]")
        
        console.print()
    
    if current_branch:
        console.print(f"[dim]* Current branch[/dim]\n")


@oss_dev_group.command(name="switch", help="Switch to a different branch or issue")
@click.argument("target", required=True)
@click.pass_context
def oss_switch(ctx: click.Context, target: str):
    """Switch to a different branch or issue."""
    from config.config import Config
    from oss.workflow import OSSWorkflow
    from oss.memory import BranchMemoryManager
    from agent.agent import Agent
    from agent.events import AgentEventType
    
    config: Config = ctx.obj["config"]
    cwd: Path = ctx.obj["cwd"]
    
    if not validate_oss_enabled(config):
        ctx.exit(1)
    
    memory_manager = BranchMemoryManager(cwd)
    
    # Try to parse as issue number
    try:
        issue_number = int(target)
        # Find branch for this issue
        branches = memory_manager.list_branches()
        target_branch = None
        
        for branch_data in branches:
            if branch_data.get("issue_number") == issue_number:
                target_branch = branch_data.get("branch_name")
                break
        
        if not target_branch:
            console.print(
                f"[error]No branch found for issue #{issue_number}.[/error]\n"
                f"Use 'oss-dev review {issue_number}' to start working on this issue."
            )
            ctx.exit(1)
        
        target = target_branch
    
    except ValueError:
        # Not an issue number, treat as branch name
        pass
    
    # Switch branch
    target_memory = memory_manager.switch_branch(target)
    
    if target_memory:
        console.print(f"[success]Switched to branch: {target}[/success]")
        
        # Show context
        summary = memory_manager.get_branch_summary(target)
        if summary.get("exists"):
            console.print(f"\n[bold]Branch Context:[/bold]")
            console.print(f"  Issue: #{summary.get('issue_number', 'N/A')}")
            console.print(f"  Phase: {summary.get('current_phase', 'unknown')}")
            console.print(f"  Status: {summary.get('status', 'unknown')}")
            if summary.get("context_summary"):
                console.print(f"  Context: {summary['context_summary']}")
        
        # Checkout branch if in git repo
        try:
            subprocess.run(
                ["git", "checkout", target],
                cwd=cwd,
                check=True,
                capture_output=True,
            )
            console.print(f"[success]Checked out branch: {target}[/success]")
        except subprocess.CalledProcessError:
            console.print(f"[warning]Could not checkout branch: {target}[/warning]")
            console.print("[dim]Branch may not exist in git. Memory context loaded.[/dim]")
        except Exception:
            pass
        
        # Resume workflow
        async def run_resume():
            workflow = OSSWorkflow(config, repository_path=cwd)
            state = await workflow.resume()
            phase_prompt = workflow.get_phase_prompt()
            
            initial_message = f"""Switched to branch: {target}

Current phase: {state.phase.value}
Issue: #{state.issue_number or 'Unknown'}

{phase_prompt}

Continue from where we left off."""
            
            console.print("\n[bold]Resuming workflow...[/bold]\n")
            
            async with Agent(config) as agent:
                async for event in agent.run(initial_message):
                    if event.type == AgentEventType.TEXT_DELTA:
                        console.print(event.data.get("content", ""), end="")
                    elif event.type == AgentEventType.TEXT_COMPLETE:
                        console.print(event.data.get("content", ""))
                    elif event.type == AgentEventType.TOOL_CALL_START:
                        tool_name = event.data.get("name", "unknown")
                        console.print(f"\n[dim]🔧 Using tool: {tool_name}[/dim]")
                    elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                        console.print("[dim]Tool complete[/dim]")
                    elif event.type == AgentEventType.AGENT_ERROR:
                        console.print(f"\n[error]{event.data.get('error', 'Unknown error')}[/error]")
        
        # Run async function
        import sys
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_resume())
        finally:
            loop.close()
    else:
        console.print(
            f"[error]No memory found for branch: {target}[/error]\n"
            f"Use 'oss-dev review <issue_number>' to start working on an issue."
        )
        ctx.exit(1)
