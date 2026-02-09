import click

@click.group()    
def oss_dev_group():
    """OSS Dev Command Group."""
    pass


def validate_oss_enabled(config) -> bool:
    if not config.oss.enabled:
        console.print(
            "[error]OSS Dev Agent is not enabled.[/error]\n"
            "Set 'oss.enabled = true' in your config file. To use this tool, ensure GITHUB_TOKEN is set as an environment variable, or add 'github_token' to the [oss] section in the config."
        )
        return False