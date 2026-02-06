"""
OSS Dev Agent CLI Commands

Click command group for OSS-specific commands.
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

console = Console()


def validate_oss_enabled(config) -> bool:
    """Check if OSS is enabled in config."""
    if not config.oss.enabled:
        console.print(
            "[error]OSS Dev Agent is not enabled.[/error]\n"
            "Set 'oss.enabled = true' in your config file or set GITHUB_TOKEN environment variable."
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
        console.print(f"[bold]Starting OSS workflow for: {issue_url}[/bold]")
        
        workflow = OSSWorkflow(config, repository_path=cwd)
        
        try:
            # Start workflow (phases 1-2 execute immediately)
            state = await workflow.start(issue_url)
            
            # Get phase prompt for Agent
            phase_prompt = workflow.get_phase_prompt()
            
            # Create initial message for Agent
            initial_message = f"""I'm working on GitHub issue: {issue_url}

Current workflow phase: {state.phase.value}

{phase_prompt}

Please use the 'workflow_orchestrator' tool to manage the workflow and proceed through the phases."""
            
            # Run Agent with workflow guidance
            async with Agent(config) as agent:
                async for event in agent.run(initial_message):
                    if event.type == AgentEventType.TEXT_DELTA:
                        console.print(event.data.get("content", ""), end="")
                    elif event.type == AgentEventType.TEXT_COMPLETE:
                        console.print(event.data.get("content", ""))
                    elif event.type == AgentEventType.TOOL_CALL_START:
                        tool_name = event.data.get("tool_name", "unknown")
                        console.print(f"\n[dim]Using tool: {tool_name}[/dim]")
                    elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                        console.print("[dim]Tool complete[/dim]")
                    elif event.type == AgentEventType.AGENT_ERROR:
                        console.print(f"\n[error]{event.data.get('error', 'Unknown error')}[/error]")
            
        except ValueError as e:
            console.print(f"[error]Invalid issue URL: {e}[/error]")
            ctx.exit(1)
        except Exception as e:
            console.print(f"[error]Failed to start OSS workflow: {e}[/error]")
            ctx.exit(1)
    
    asyncio.run(run_fix())


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
                        tool_name = event.data.get("tool_name", "unknown")
                        console.print(f"\n[dim]Using tool: {tool_name}[/dim]")
                    elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                        console.print("[dim]Tool complete[/dim]")
                    elif event.type == AgentEventType.AGENT_ERROR:
                        console.print(f"\n[error]{event.data.get('error', 'Unknown error')}[/error]")
        
        except Exception as e:
            console.print(f"[error]Failed to start OSS workflow: {e}[/error]")
            ctx.exit(1)
    
    asyncio.run(run_review())


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
                        tool_name = event.data.get("tool_name", "unknown")
                        console.print(f"\n[dim]Using tool: {tool_name}[/dim]")
                    elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                        console.print("[dim]Tool complete[/dim]")
                    elif event.type == AgentEventType.AGENT_ERROR:
                        console.print(f"\n[error]{event.data.get('error', 'Unknown error')}[/error]")
        
        except Exception as e:
            console.print(f"[error]Failed to resume workflow: {e}[/error]")
            ctx.exit(1)
    
    asyncio.run(run_resume())


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
    
    console.print("\n[bold]OSS Workflow Status[/bold]")
    console.print("─" * 50)
    
    if current_branch:
        console.print(f"  Branch: [cyan]{current_branch}[/cyan]")
    else:
        console.print("  Branch: [dim]Not in a git repository[/dim]")
    
    if phase_info.get('issue_number'):
        console.print(f"  Issue: [cyan]#{phase_info['issue_number']}[/cyan]")
        if phase_info.get('issue_url'):
            console.print(f"  URL: [dim]{phase_info['issue_url']}[/dim]")
    
    console.print(f"  Phase: [yellow]{phase_info['phase']}[/yellow]")
    console.print(f"  Changes Made: {'[green]Yes[/green]' if phase_info.get('changes_made') else '[dim]No[/dim]'}")
    console.print(f"  Tests Passed: {'[green]Yes[/green]' if phase_info.get('tests_passed') else '[dim]No[/dim]'}")
    
    if phase_info.get('pr_url'):
        console.print(f"  PR: [cyan]{phase_info['pr_url']}[/cyan]")
    
    # Get branch summary if available
    if current_branch:
        summary = memory_manager.get_branch_summary(current_branch)
        if summary.get("exists"):
            if summary.get("context_summary"):
                console.print(f"\n  Context: [dim]{summary['context_summary']}[/dim]")
            if summary.get("files_modified", 0) > 0:
                console.print(f"  Files Modified: {summary['files_modified']}")
    
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
            console.print("\n[bold]Uncommitted Changes:[/bold]")
            console.print(result.stdout)
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
                        tool_name = event.data.get("tool_name", "unknown")
                        console.print(f"\n[dim]Using tool: {tool_name}[/dim]")
                    elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                        console.print("[dim]Tool complete[/dim]")
                    elif event.type == AgentEventType.AGENT_ERROR:
                        console.print(f"\n[error]{event.data.get('error', 'Unknown error')}[/error]")
        
        asyncio.run(run_resume())
    else:
        console.print(
            f"[error]No memory found for branch: {target}[/error]\n"
            f"Use 'oss-dev review <issue_number>' to start working on an issue."
        )
        ctx.exit(1)
