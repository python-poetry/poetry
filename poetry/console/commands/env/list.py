from ..command import Command


class EnvListCommand(Command):
    """
    List all virtualenvs associated with the current project.

    list
        {--full-path : Output the full paths of the virtualenvs}
    """

    def handle(self):
        from poetry.utils.env import EnvManager

        poetry = self.poetry
        manager = EnvManager(poetry.config)
        current_env = manager.get(self.poetry.file.parent)

        for venv in manager.list(self.poetry.file.parent):
            name = venv.path.name
            if self.option("full-path"):
                name = str(venv.path)

            if venv == current_env:
                self.line("<info>{} (Activated)</info>".format(name))

                continue

            self.line(name)
