# Plugin Development Guide

## Overview

OSS-Dev supports plugins that extend CLI commands, tools, and hooks. Plugins are discoverable via Python entry points.

## Quick Start

```python
from oss_dev.core.contracts.plugin import Plugin, PluginManifest, Command

class MyPlugin(Plugin):
    name = "my-plugin"
    version = "0.1.0"
    description = "My custom plugin"

    async def initialize(self, config):
        # Setup resources
        pass

    async def shutdown(self):
        # Cleanup resources
        pass

    def get_commands(self):
        return [
            Command(
                name="my-command",
                help_text="My custom command",
                callback=self.my_command,
            )
        ]

    async def my_command(self):
        print("Hello from my plugin!")
```

## Entry Point Registration

In your `pyproject.toml`:

```toml
[project.entry-points."oss_dev.plugins"]
my-plugin = "my_package:MyPlugin"
```

## Plugin Lifecycle

1. **LOAD** — Plugin module is imported
2. **VALIDATE** — Manifest is checked
3. **INITIALIZE** — `initialize(config)` is called
4. **REGISTER** — Commands, tools, hooks are registered
5. **SHUTDOWN** — `shutdown()` is called on exit

## Built-in Plugins

Built-in plugins live in `src/oss_dev/plugins/builtins/` and are loaded automatically.

## Hooks

Plugins can hook into agent lifecycle:

```python
def get_hooks(self):
    return {
        "before_tool": self.before_tool,
        "after_tool": self.after_tool,
    }
```

## Testing

```python
from oss_dev.plugins.loader import PluginLoader

async def test_my_plugin():
    loader = PluginLoader()
    plugin = await loader.load("my_package:MyPlugin")
    assert plugin.name == "my-plugin"
```
