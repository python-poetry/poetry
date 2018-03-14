from poetry.utils.venv import Venv

from .command import Command


class VenvCommand(Command):

    def __init__(self, name=None):
        self._venv = None

        super().__init__(name)

    def initialize(self, i, o):
        super().initialize(i, o)

        self._venv = Venv.create(o, self.poetry.package.name)

        if self._venv.is_venv() and o.is_verbose():
            o.writeln(f'Using virtualenv: <comment>{self._venv.venv}</>')

    @property
    def venv(self):
        return self._venv
