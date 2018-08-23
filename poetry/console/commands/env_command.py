from .command import Command


class EnvCommand(Command):
    def __init__(self):
        self._env = None

        super(EnvCommand, self).__init__()

    def initialize(self, i, o):
        from poetry.utils.env import Env

        super(EnvCommand, self).initialize(i, o)

        self._env = Env.create_venv(
            o, self.poetry.package.name, cwd=self.poetry.file.parent
        )

        if self._env.is_venv() and o.is_verbose():
            o.writeln("Using virtualenv: <comment>{}</>".format(self._env.path))

    @property
    def env(self):
        return self._env
