from cleo import option

from ..command import Command


class EnvListCommand(Command):

    name = "list"
    description = "Lists all virtualenvs associated with the current project."

    options = [option("full-path", None, "Output the full paths of the virtualenvs.")]

    def handle(self):
        from poetry.utils.env import EnvManager

        manager = EnvManager(self.poetry)
        current_env = manager.get()
        env_list = manager.list()
        if (
            self.poetry.config.get("virtualenvs.in-project")
            and current_env not in env_list
        ):
            env_list.insert(0, current_env)

        for venv in env_list:
            name = venv.path.name
            if self.option("full-path"):
                name = str(venv.path)

            if venv == current_env:
                self.line("<info>{} (Activated)</info>".format(name))

                continue

            self.line(name)
