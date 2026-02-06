import asyncio
from pathlib import Path
import sys
import click

from agent.agent import Agent
from agent.events import AgentEventType
from agent.persistence import PersistenceManager, SessionSnapshot
from agent.session import Session
from config.config import ApprovalPolicy, Config
from config.loader import load_config
from ui.tui import TUI, get_console
from oss.workflow import OSSWorkflow

console = get_console()


class CLI:
    def __init__(self, config: Config):
        self.agent: Agent | None = None
        self.config = config
        self.tui = TUI(config, console)

    async def run_single(self, message: str) -> str | None:
        async with Agent(self.config) as agent:
            self.agent = agent
            return await self._process_message(message)

    async def run_interactive(self) -> str | None:
        self.tui.print_welcome(
            "AI Agent",
            lines=[
                f"model: {self.config.model_name}",
                f"cwd: {self.config.cwd}",
                "commands: /help /config /approval /model /exit",
            ],
        )

        async with Agent(
            self.config,
            confirmation_callback=self.tui.handle_confirmation,
        ) as agent:
            self.agent = agent

            while True:
                try:
                    user_input = console.input("\n[user]>[/user] ").strip()
                    if not user_input:
                        continue

                    if user_input.startswith("/"):
                        should_continue = await self._handle_command(user_input)
                        if not should_continue:
                            break
                        continue

                    await self._process_message(user_input)
                except KeyboardInterrupt:
                    console.print("\n[dim]Use /exit to quit[/dim]")
                except EOFError:
                    break

        console.print("\n[dim]Goodbye![/dim]")

    def _get_tool_kind(self, tool_name: str) -> str | None:
        tool_kind = None
        tool = self.agent.session.tool_registry.get(tool_name)
        if not tool:
            tool_kind = None

        tool_kind = tool.kind.value

        return tool_kind

    async def _process_message(self, message: str) -> str | None:
        if not self.agent:
            return None

        assistant_streaming = False
        final_response: str | None = None

        async for event in self.agent.run(message):
            if event.type == AgentEventType.TEXT_DELTA:
                content = event.data.get("content", "")
                if not assistant_streaming:
                    self.tui.begin_assistant()
                    assistant_streaming = True
                self.tui.stream_assistant_delta(content)
            elif event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")
                if assistant_streaming:
                    self.tui.end_assistant()
                    assistant_streaming = False
            elif event.type == AgentEventType.AGENT_ERROR:
                error = event.data.get("error", "Unknown error")
                console.print(f"\n[error]Error: {error}[/error]")
            elif event.type == AgentEventType.TOOL_CALL_START:
                tool_name = event.data.get("name", "unknown")
                tool_kind = self._get_tool_kind(tool_name)
                self.tui.tool_call_start(
                    event.data.get("call_id", ""),
                    tool_name,
                    tool_kind,
                    event.data.get("arguments", {}),
                )
            elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                tool_name = event.data.get("name", "unknown")
                tool_kind = self._get_tool_kind(tool_name)
                self.tui.tool_call_complete(
                    event.data.get("call_id", ""),
                    tool_name,
                    tool_kind,
                    event.data.get("success", False),
                    event.data.get("output", ""),
                    event.data.get("error"),
                    event.data.get("metadata"),
                    event.data.get("diff"),
                    event.data.get("truncated", False),
                    event.data.get("exit_code"),
                )

        return final_response

    async def _handle_command(self, command: str) -> bool:
        cmd = command.lower().strip()
        parts = cmd.split(maxsplit=1)
        cmd_name = parts[0]
        cmd_args = parts[1] if len(parts) > 1 else ""
        if cmd_name == "/exit" or cmd_name == "/quit":
            return False
        elif command == "/help":
            self.tui.show_help()
        elif command == "/clear":
            self.agent.session.context_manager.clear()
            self.agent.session.loop_detector.clear()
            console.print("[success]Conversation cleared [/success]")
        elif command == "/config":
            console.print("\n[bold]Current Configuration[/bold]")
            console.print(f"  Model: {self.config.model_name}")
            console.print(f"  Temperature: {self.config.temperature}")
            console.print(f"  Approval: {self.config.approval.value}")
            console.print(f"  Working Dir: {self.config.cwd}")
            console.print(f"  Max Turns: {self.config.max_turns}")
            console.print(f"  Hooks Enabled: {self.config.hooks_enabled}")
        elif cmd_name == "/model":
            if cmd_args:
                self.config.model_name = cmd_args
                console.print(f"[success]Model changed to: {cmd_args} [/success]")
            else:
                console.print(f"Current model: {self.config.model_name}")
        elif cmd_name == "/approval":
            if cmd_args:
                try:
                    approval = ApprovalPolicy(cmd_args)
                    self.config.approval = approval
                    console.print(
                        f"[success]Approval policy changed to: {cmd_args} [/success]"
                    )
                except:
                    console.print(
                        f"[error]Incorrect approval policy: {cmd_args} [/error]"
                    )
                    console.print(
                        f"Valid options: {', '.join(p for p in ApprovalPolicy)}"
                    )
            else:
                console.print(f"Current approval policy: {self.config.approval.value}")
        elif cmd_name == "/stats":
            stats = self.agent.session.get_stats()
            console.print("\n[bold]Session Statistics [/bold]")
            for key, value in stats.items():
                console.print(f"   {key}: {value}")
        elif cmd_name == "/tools":
            tools = self.agent.session.tool_registry.get_tools()
            console.print(f"\n[bold]Available tools ({len(tools)}) [/bold]")
            for tool in tools:
                console.print(f"  • {tool.name}")
        elif cmd_name == "/mcp":
            mcp_servers = self.agent.session.mcp_manager.get_all_servers()
            console.print(f"\n[bold]MCP Servers ({len(mcp_servers)}) [/bold]")
            for server in mcp_servers:
                status = server["status"]
                status_color = "green" if status == "connected" else "red"
                console.print(
                    f"  • {server['name']}: [{status_color}]{status}[/{status_color}] ({server['tools']} tools)"
                )
        elif cmd_name == "/save":
            persistence_manager = PersistenceManager()
            session_snapshot = SessionSnapshot(
                session_id=self.agent.session.session_id,
                created_at=self.agent.session.created_at,
                updated_at=self.agent.session.updated_at,
                turn_count=self.agent.session.turn_count,
                messages=self.agent.session.context_manager.get_messages(),
                total_usage=self.agent.session.context_manager.total_usage,
            )
            persistence_manager.save_session(session_snapshot)
            console.print(
                f"[success]Session saved: {self.agent.session.session_id}[/success]"
            )
        elif cmd_name == "/sessions":
            persistence_manager = PersistenceManager()
            sessions = persistence_manager.list_sessions()
            console.print("\n[bold]Saved Sessions[/bold]")
            for s in sessions:
                console.print(
                    f"  • {s['session_id']} (turns: {s['turn_count']}, updated: {s['updated_at']})"
                )
        elif cmd_name == "/resume":
            if not cmd_args:
                console.print(f"[error]Usage: /resume <session_id> [/error]")
            else:
                persistence_manager = PersistenceManager()
                snapshot = persistence_manager.load_session(cmd_args)
                if not snapshot:
                    console.print(f"[error]Session does not exist [/error]")
                else:
                    session = Session(
                        config=self.config,
                    )
                    await session.initialize()
                    session.session_id = snapshot.session_id
                    session.created_at = snapshot.created_at
                    session.updated_at = snapshot.updated_at
                    session.turn_count = snapshot.turn_count
                    session.context_manager.total_usage = snapshot.total_usage

                    for msg in snapshot.messages:
                        if msg.get("role") == "system":
                            continue
                        elif msg["role"] == "user":
                            session.context_manager.add_user_message(
                                msg.get("content", "")
                            )
                        elif msg["role"] == "assistant":
                            session.context_manager.add_assistant_message(
                                msg.get("content", ""), msg.get("tool_calls")
                            )
                        elif msg["role"] == "tool":
                            session.context_manager.add_tool_result(
                                msg.get("tool_call_id", ""), msg.get("content", "")
                            )

                    await self.agent.session.client.close()
                    await self.agent.session.mcp_manager.shutdown()

                    self.agent.session = session
                    console.print(
                        f"[success]Resumed session: {session.session_id}[/success]"
                    )
        elif cmd_name == "/checkpoint":
            persistence_manager = PersistenceManager()
            session_snapshot = SessionSnapshot(
                session_id=self.agent.session.session_id,
                created_at=self.agent.session.created_at,
                updated_at=self.agent.session.updated_at,
                turn_count=self.agent.session.turn_count,
                messages=self.agent.session.context_manager.get_messages(),
                total_usage=self.agent.session.context_manager.total_usage,
            )
            checkpoint_id = persistence_manager.save_checkpoint(session_snapshot)
            console.print(f"[success]Checkpoint created: {checkpoint_id}[/success]")
        elif cmd_name == "/restore":
            if not cmd_args:
                console.print(f"[error]Usage: /restire <checkpoint_id> [/error]")
            else:
                persistence_manager = PersistenceManager()
                snapshot = persistence_manager.load_checkpoint(cmd_args)
                if not snapshot:
                    console.print(f"[error]Checkpoint does not exist [/error]")
                else:
                    session = Session(
                        config=self.config,
                    )
                    await session.initialize()
                    session.session_id = snapshot.session_id
                    session.created_at = snapshot.created_at
                    session.updated_at = snapshot.updated_at
                    session.turn_count = snapshot.turn_count
                    session.context_manager.total_usage = snapshot.total_usage

                    for msg in snapshot.messages:
                        if msg.get("role") == "system":
                            continue
                        elif msg["role"] == "user":
                            session.context_manager.add_user_message(
                                msg.get("content", "")
                            )
                        elif msg["role"] == "assistant":
                            session.context_manager.add_assistant_message(
                                msg.get("content", ""), msg.get("tool_calls")
                            )
                        elif msg["role"] == "tool":
                            session.context_manager.add_tool_result(
                                msg.get("tool_call_id", ""), msg.get("content", "")
                            )

                    await self.agent.session.client.close()
                    await self.agent.session.mcp_manager.shutdown()

                    self.agent.session = session
                    console.print(
                        f"[success]Resumed session: {session.session_id}, checkpoint: {checkpoint_id}[/success]"
                    )
        elif cmd_name == "/oss-fix":
            if not cmd_args:
                console.print(f"[error]Usage: /oss-fix <github_issue_url> [/error]")
            else:
                await self._handle_oss_fix(cmd_args)
        elif cmd_name == "/oss-review":
            if not cmd_args:
                console.print(f"[error]Usage: /oss-review <issue_number> [/error]")
            else:
                await self._handle_oss_review(cmd_args)
        elif cmd_name == "/oss-resume":
            await self._handle_oss_resume()
        elif cmd_name == "/oss-status":
            await self._handle_oss_status()
        else:
            console.print(f"[error]Unknown command: {cmd_name}[/error]")

        return True

    async def _handle_oss_fix(self, issue_url: str) -> None:
        """Handle oss-dev fix command."""
        if not self.config.oss.enabled:
            console.print("[error]OSS Dev Agent is not enabled. Set oss.enabled=true in config.[/error]")
            return

        console.print(f"[bold]Starting OSS workflow for: {issue_url}[/bold]")
        
        workflow = OSSWorkflow(self.config)
        
        # Start workflow (phases 1-2 execute immediately)
        try:
            state = await workflow.start(issue_url)
            
            # Get phase prompt for Agent
            phase_prompt = workflow.get_phase_prompt()
            
            # Create initial message for Agent
            initial_message = f"""I'm working on GitHub issue: {issue_url}

Current workflow phase: {state.phase.value}

{phase_prompt}

Please use the 'workflow_orchestrator' tool to manage the workflow and proceed through the phases."""
            
            # Run Agent with workflow guidance
            await self._process_message(initial_message)
            
        except Exception as e:
            console.print(f"[error]Failed to start OSS workflow: {e}[/error]")

    async def _handle_oss_review(self, issue_number: str) -> None:
        """Handle oss-dev review command."""
        if not self.config.oss.enabled:
            console.print("[error]OSS Dev Agent is not enabled. Set oss.enabled=true in config.[/error]")
            return

        try:
            issue_num = int(issue_number)
        except ValueError:
            console.print(f"[error]Invalid issue number: {issue_number}[/error]")
            return

        # Try to get repo from current directory
        import subprocess
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.config.cwd,
                capture_output=True,
                text=True,
                check=True,
            )
            url = result.stdout.strip()
            # Parse to get owner/repo
            if "github.com" in url:
                parts = url.replace(".git", "").split("github.com/")[-1].split("/")
                if len(parts) >= 2:
                    owner, repo = parts[0], parts[1]
                    issue_url = f"https://github.com/{owner}/{repo}/issues/{issue_num}"
                    await self._handle_oss_fix(issue_url)
                    return
        except Exception:
            pass

        console.print(f"[error]Could not determine repository. Please provide full issue URL.[/error]")

    async def _handle_oss_resume(self) -> None:
        """Handle oss-dev resume command."""
        if not self.config.oss.enabled:
            console.print("[error]OSS Dev Agent is not enabled. Set oss.enabled=true in config.[/error]")
            return

        workflow = OSSWorkflow(self.config)
        
        try:
            state = await workflow.resume()
            phase_prompt = workflow.get_phase_prompt()
            
            initial_message = f"""Resuming OSS workflow.

Current phase: {state.phase.value}
Issue: #{state.issue_number or 'Unknown'}
Branch: {state.branch_name or 'Not created'}

{phase_prompt}

Continue from where we left off."""
            
            await self._process_message(initial_message)
            
        except Exception as e:
            console.print(f"[error]Failed to resume workflow: {e}[/error]")

    async def _handle_oss_status(self) -> None:
        """Handle oss-dev status command."""
        if not self.config.oss.enabled:
            console.print("[error]OSS Dev Agent is not enabled. Set oss.enabled=true in config.[/error]")
            return

        workflow = OSSWorkflow(self.config)
        phase_info = workflow.get_current_phase_info()
        
        console.print("\n[bold]OSS Workflow Status[/bold]")
        console.print(f"  Phase: {phase_info['phase']}")
        if phase_info.get('issue_number'):
            console.print(f"  Issue: #{phase_info['issue_number']}")
        if phase_info.get('branch_name'):
            console.print(f"  Branch: {phase_info['branch_name']}")
        console.print(f"  Changes Made: {phase_info['changes_made']}")
        console.print(f"  Tests Passed: {phase_info['tests_passed']}")
        if phase_info.get('pr_url'):
            console.print(f"  PR: {phase_info['pr_url']}")
        
        # Show git status if in repo
        import subprocess
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=self.config.cwd,
                capture_output=True,
                text=True,
                check=True,
            )
            if result.stdout.strip():
                console.print("\n[bold]Uncommitted Changes:[/bold]")
                console.print(result.stdout)
        except Exception:
            pass


@click.group(invoke_without_command=True)
@click.argument("prompt", required=False)
@click.option(
    "--cwd",
    "-c",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Current working directory",
)
@click.pass_context
def main(
    ctx: click.Context,
    prompt: str | None,
    cwd: Path | None,
):
    """
    AI Coding Agent - CLI interface for AI-powered coding assistance.
    
    Use 'oss-dev' subcommands for OSS contribution workflows.
    """
    # If a subcommand was invoked, don't run the default behavior
    if ctx.invoked_subcommand is not None:
        return
    
    try:
        config = load_config(cwd=cwd)
    except Exception as e:
        console.print(f"[error]Configuration Error: {e}[/error]")
        sys.exit(1)

    errors = config.validate()

    if errors:
        for error in errors:
            console.print(f"[error]{error}[/error]")
        sys.exit(1)

    cli = CLI(config)

    # messages = [{"role": "user", "content": prompt}]
    if prompt:
        result = asyncio.run(cli.run_single(prompt))
        if result is None:
            sys.exit(1)
    else:
        asyncio.run(cli.run_interactive())


# Add OSS command group
from cli.oss_commands import oss_dev_group
main.add_command(oss_dev_group)

if __name__ == "__main__":
    main()
