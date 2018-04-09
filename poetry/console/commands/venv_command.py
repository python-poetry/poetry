from .command import Command


class VenvCommand(Command):

    def __init__(self, name=None):
        self._venv = None

        super(VenvCommand, self).__init__(name)

    def initialize(self, i, o):
        from poetry.utils.venv import Venv

        super(VenvCommand, self).initialize(i, o)

        self._venv = Venv.create(o, self.poetry.package.name)

        if self._venv.is_venv() and o.is_verbose():
            o.writeln(
                'Using virtualenv: <comment>{}</>'.format(self._venv.venv)
            )

    @property
    def venv(self):
        return self._venv
