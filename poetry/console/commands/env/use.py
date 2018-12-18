from ..command import Command


class EnvUseCommand(Command):
    """
    Activate or create a new virtualenv for the current project.

    use
        {python : The python executable to use.}
    """

    def handle(self):
        from poetry.utils.env import EnvManager

        poetry = self.poetry
        manager = EnvManager(poetry.config)

        if self.argument("python") == "system":
            manager.deactivate(poetry.file.parent, self._io)

            return

        env = manager.activate(self.argument("python"), poetry.file.parent, self._io)

        self.line("Using virtualenv: <comment>{}</>".format(env.path))
