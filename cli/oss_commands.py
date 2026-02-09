import click

@click.group()
def oss_dev_group():
    """OSS Dev Agent"""
    pass

@oss_dev_group.command(name='fix')
@click.argument('url', required=True)
def fix_command(url):
    click.echo("Fixing issue at:", url)

@oss_dev_group.command(name='review')
@click.argument('issue_number', required=True)
def review_command(issue_number):
    click.echo("Reviewing issue:", issue_number)

@oss_dev_group.command(name='status')
def status_command():
    click.echo("This command shows the status.")

@oss_dev_group.command(name='list')
def list_command():
    click.echo("This command lists issues.")

@oss_dev_group.command(name='switch')
@click.argument('target', required=True)
def switch_command(target):
    click.echo("Switching to target:", target)


def validate_oss_enabled(config) -> bool:
    if not config.oss.enabled:
        console.print(
            "[error]OSS Dev Agent is not enabled.[/error]\n"
            "Set 'oss.enabled = true' in your config file. To use this tool, ensure GITHUB_TOKEN is set as an environment variable, or add 'github_token' to the [oss] section in the config."
        )
        return False