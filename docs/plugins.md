---
title: "Plugins"
draft: false
type: docs
layout: single

menu:
  docs:
    weight: 80
---

# Plugins

Poetry supports using and building plugins if you wish to
alter or expand Poetry's functionality with your own.

For example if your environment poses special requirements
on the behaviour of Poetry which do not apply to the majority of its users
or if you wish to accomplish something with Poetry in a way that is not desired by most users.

In these cases you could consider creating a plugin to handle your specific logic.


## Creating a plugin

A plugin is a regular Python package which ships its code as part of the package
and may also depend on further packages.

### Plugin package

The plugin package must depend on Poetry
and declare a proper [plugin]({{< relref "pyproject#plugins" >}}) in the `pyproject.toml` file.

```toml
[project]
name = "my-poetry-plugin"
version = "1.0.0"
# ...
requires-python = ">=3.7"
dependencies = [
    "poetry (>=1.2,<2.0)",
]

[project.entry-points."poetry.plugin"]
demo = "poetry_demo_plugin.plugin:MyPlugin"
```

### Generic plugins

Every plugin has to supply a class which implements the `poetry.plugins.Plugin` interface.

The `activate()` method of the plugin is called after the plugin is loaded
and receives an instance of `Poetry` as well as an instance of `cleo.io.io.IO`.

Using these two objects all configuration can be read
and all public internal objects and state can be manipulated as desired.

Example:

```python
from cleo.io.io import IO

from poetry.plugins.plugin import Plugin
from poetry.poetry import Poetry


class MyPlugin(Plugin):

    def activate(self, poetry: Poetry, io: IO):
        io.write_line("Setting readme")
        poetry.package.readme = "README.md"
        ...
```

### Application plugins

If you want to add commands or options to the `poetry` script you need
to create an application plugin which implements the `poetry.plugins.ApplicationPlugin` interface.

The `activate()` method of the application plugin is called after the plugin is loaded
and receives an instance of `poetry.console.Application`.

```python
from cleo.commands.command import Command
from poetry.plugins.application_plugin import ApplicationPlugin


class CustomCommand(Command):

    name = "my-command"

    def handle(self) -> int:
        self.line("My command")

        return 0


def factory():
    return CustomCommand()


class MyApplicationPlugin(ApplicationPlugin):
    def activate(self, application):
        application.command_loader.register_factory("my-command", factory)
```

{{% note %}}
It's possible to do the following to register the command:

```python
application.add(MyCommand())
```

However, it is **strongly** recommended to register a new factory
in the command loader to defer the loading of the command when it's actually
called.

This will help keep the performances of Poetry good.
{{% /note %}}

The plugin also must be declared in the `pyproject.toml` file of the plugin package
as a `poetry.application.plugin` plugin:

```toml
[tool.poetry.plugins."poetry.application.plugin"]
foo-command = "poetry_demo_plugin.plugin:MyApplicationPlugin"
```

{{% warning %}}
A plugin **must not** remove or modify in any way the core commands of Poetry.
{{% /warning %}}


### Event handler

Plugins can also listen to specific events and act on them if necessary.

These events are fired by [Cleo](https://github.com/python-poetry/cleo)
and are accessible from the `cleo.events.console_events` module.

- `COMMAND`: this event allows attaching listeners before any command is executed.
- `SIGNAL`: this event allows some actions to be performed after the command execution is interrupted.
- `TERMINATE`: this event allows listeners to be attached after the command.
- `ERROR`: this event occurs when an uncaught exception is raised.

Let's see how to implement an application event handler. For this example
we will see how to load environment variables from a `.env` file before executing
a command.


```python
from cleo.events.console_events import COMMAND
from cleo.events.console_command_event import ConsoleCommandEvent
from cleo.events.event_dispatcher import EventDispatcher
from dotenv import load_dotenv
from poetry.console.application import Application
from poetry.console.commands.env_command import EnvCommand
from poetry.plugins.application_plugin import ApplicationPlugin


class MyApplicationPlugin(ApplicationPlugin):
    def activate(self, application: Application):
        application.event_dispatcher.add_listener(
            COMMAND, self.load_dotenv
        )

    def load_dotenv(
        self,
        event: ConsoleCommandEvent,
        event_name: str,
        dispatcher: EventDispatcher
    ) -> None:
        command = event.command
        if not isinstance(command, EnvCommand):
            return

        io = event.io

        if io.is_debug():
            io.write_line(
                "<debug>Loading environment variables.</debug>"
            )

        load_dotenv()
```


## Using plugins

Installed plugin packages are automatically loaded when Poetry starts up.

You have multiple ways to install plugins for Poetry

### With `pipx inject`

If you used `pipx` to install Poetry you can add the plugin packages via the `pipx inject` command.

```shell
pipx inject poetry poetry-plugin
```

If you want to uninstall a plugin, you can run:

```shell
pipx uninject poetry poetry-plugin          # For pipx versions >= 1.2.0

pipx runpip poetry uninstall poetry-plugin  # For pipx versions  < 1.2.0
```

### With `pip`

The `pip` binary in Poetry's virtual environment can also be used to install and remove plugins.
The environment variable `$POETRY_HOME` here is used to represent the path to the virtual environment.
The [installation instructions](/docs/) can be referenced if you are not
sure where Poetry has been installed.

To add a plugin, you can use `pip install`:

```shell
$POETRY_HOME/bin/pip install --user poetry-plugin
```

If you want to uninstall a plugin, you can run:

```shell
$POETRY_HOME/bin/pip uninstall poetry-plugin
```

### The `self add` command

{{% warning %}}
Especially on Windows, `self add` and `self remove` may be problematic
so that other methods should be preferred.
{{% /warning %}}

```bash
poetry self add poetry-plugin
```

The `self add` command will ensure that the plugin is compatible with the current version of Poetry
and install the needed packages for the plugin to work.

The package specification formats supported by the `self add` command are the same as the ones supported
by the [`add` command]({{< relref "cli#add" >}}).

If you no longer need a plugin and want to uninstall it, you can use the `self remove` command.

```shell
poetry self remove poetry-plugin
```

You can also list all currently installed plugins by running:

```shell
poetry self show plugins
```

### Project plugins

You can also specify that a plugin is required for your project
in the `tool.poetry.requires-plugins` section of the pyproject.toml file:

```toml
[tool.poetry.requires-plugins]
my-application-plugin = ">1.0"
custom-plugin = {path = "custom_plugin", develop = true}
```

If the plugin is not installed in Poetry's own environment when running `poetry install`,
it will be installed only for the current project under `.poetry/plugins`
in the project's directory.

The syntax to specify `plugins` is the same as for [dependencies]({{< relref "managing-dependencies" >}}).
Plugins can be installed in editable mode using path dependencies with `develop = true`,
which is useful for plugin development.

{{% warning %}}
You can even overwrite a plugin in Poetry's own environment with another version.
However, if a plugin's dependencies are not compatible with packages in Poetry's own
environment, installation will fail.
{{% /warning %}}


## Maintaining a plugin

When writing a plugin, you will probably access internals of Poetry, since there is no
stable public API. Although we try our best to deprecate methods first, before
removing them, sometimes the signature of an internal method has to be changed.

As the author of a plugin, you are probably testing your plugin
against the latest release of Poetry.
Additionally, you should consider testing against the latest release branch and the
main branch of Poetry and schedule a CI job that runs regularly even if you did not
make any changes to your plugin.
This way, you will notice internal changes that break your plugin immediately
and can prepare for the next Poetry release.
