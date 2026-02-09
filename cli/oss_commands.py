import click

@click.group()
def oss_dev_group():
    """OSS Dev Command Group."""
    pass

@oss_dev_group.command(name='fix')
def fix_command():
    click.echo("This command fixes an issue.")

@oss_dev_group.command(name='review')
def review_command():
    click.echo("This command reviews an issue.")

@oss_dev_group.command(name='status')
def status_command():
    click.echo("This command shows the status.")

@oss_dev_group.command(name='list')
def list_command():
    click.echo("This command lists issues.")

@oss_dev_group.command(name='switch')
def switch_command():
    click.echo("This command switches the context.")


def validate_oss_enabled(config) -> bool:
    if not config.oss.enabled:
        console.print(
            "[error]OSS Dev Agent is not enabled.[/error]\n"
            "Set 'oss.enabled = true' in your config file. To use this tool, ensure GITHUB_TOKEN is set as an environment variable, or add 'github_token' to the [oss] section in the config."
        )
        return False