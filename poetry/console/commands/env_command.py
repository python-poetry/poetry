from .command import Command


class EnvCommand(Command):
    def __init__(self):
        self._env = None

        super(EnvCommand, self).__init__()

    @property
    def env(self):
        return self._env

    def set_env(self, env):
        self._env = env
