# Plugins

You may wish to alter or expand Poetry's functionality with your own.
For example if your environment poses special requirements
on the behaviour of Poetry which do not apply to the majority of its users
or if you wish to accomplish something with Poetry in a way that is not desired by most users.

In these cases you could consider creating a plugin to handle your specific logic.


## Creating a plugin

A plugin is a regular Python package which ships its code as part of the package
and may also depend on further packages.

### Plugin package

The plugin package must depend on Poetry
and declare a proper [plugin](/docs/pyproject/#plugins) in the `pyproject.toml` file.

```toml
[tool.poetry]
name = "my-poetry-plugin"
version = "1.0.0"
# ...

[tool.poetry.dependency]
python = "~2.7 || ^3.7"
poetry = "^1.0"

[tool.poetry.plugins."poetry.plugin"]
demo = "poetry_demo_plugin.plugin:MyPlugin"
```

### Generic plugins

Every plugin has to supply a class which implements the `poetry.plugins.Plugin` interface.

The `activate()` method of the plugin is called after the plugin is loaded
and receives an instance of `Poetry` as well as an instance of `clikit.api.io.IO`.

Using these two objects all configuration can be read
and all internal objects and state can be manipulated as desired.

Example:

```python
from poetry.plugins import Plugin


class MyPlugin(Plugin):

    def activate(self, poetry, io):  # type: (Poetry, IO) -> None
        version = self.get_custom_version()
        io.write_line("Setting package version to {}".format(version))

        poetry.package.version = version

    def get_custom_version(self):  # type: () -> str
        ...
```

### Application plugins

If you want to add commands or options to the `poetry` script you need
to create an application plugin which implements the `poetry.plugins.ApplicationPlugin` interface.

The `activate()` method of the application plugin is called after the plugin is loaded
and receives an instance of `console.Application`.

```python
from poetry.plugins import ApplicationPlugin


class MyApplicationPlugin(ApplicationPlugin):

    def activate(self, application):
        application.add(FooCommand())
```

It also must be declared in the `pyproject.toml` file as a `application.plugin` plugin:

```toml
[tool.poetry.plugins."poetry.application.plugin"]
foo-command = "poetry_demo_plugin.plugin:MyApplicationPlugin"
```


### Event handler

Plugins can also listens to specific events and act on them if necessary.

There are two types of events: application events and generic events.

All event types are represented by the `poetry.events.Events` enum class.
Here are the various events fired during Poetry's execution process:

- `APPLICATION_BOOT`: occurs before the application is fully booted.

And since Poetry's application is powered by [CliKit](https://github.com/sdispater/clikit),
the following events are also fired. Note that all events are accessible from
the `clikit.api.event.ConsoleEvents` enum.

- `PRE_RESOLVE`: occurs before resolving the command.
- `PRE_HANDLE`: occurs before the command is executed.
- `CONFIG`: occurs before the application's configuration is finalized.

Let's see how to implement an application event handler. For this example
we want to add an option to the application and, if it is set, trigger
a specific handler.

!!!note

    This is how the `-h/--help` option of poetry works.

```python
from clikit.api.event import ConsoleEvents
from clikit.api.resolver import ResolvedCommand
from poetry.plugins import ApplicationPlugin


class MyApplicationPlugin(ApplicationPlugin):

    def activate(self, application):
        application.config.add_option("foo", description="Call the foo command")
        application.add_command(FooCommmand())
        application.event_dispatcher.add_listener(ConsoleEvents.PRE_RESOLVE, self.resolve_foo_command)

    def resolve_foo_command(self, event, event_name, dispatcher):
        # The event is a PreResolveEvent instance which gives
        # access to the raw arguments and the application
        args = event.raw_args
        application = event.application

        if args.has_token("--foo"):
            command = application.find("foo")

            # Enable lenient parsing
            parsed_args = command.parse(args, True)

            event.set_resolved_command(ResolvedCommand(command, parsed_args))

            # Since we have properly resolved the command
            # there is no need to go further, so we stop
            # the event propagation.
            event.stop_propagation()
```
