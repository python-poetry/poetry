from ..command import Command


class EnvPathCommand(Command):

    name = "path"
    description = "Outputs the absolute path to the currently activated virtualenv."

    def handle(self):
        from poetry.utils.env import EnvManager

        manager = EnvManager(self.poetry)
        current_env = manager.get()
        self.line(str(current_env.path))
