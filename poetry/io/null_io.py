from poetry.console.styles.poetry import PoetryStyle
from poetry.utils.venv import Venv


class NullVenv(Venv):

    def __init__(self, execute=False):
        super().__init__()

        self.executed = []
        self._execute = execute

    def run(self, bin: str, *args):
        self.executed.append([bin] + list(args))

        if self._execute:
            return super().run(bin, *args)

    def _bin(self, bin):
        return bin


class NullIO(PoetryStyle):

    def __init__(self, execute=False):
        self._venv = NullVenv(execute=execute)

    @property
    def venv(self) -> NullVenv:
        return self._venv

    def is_quiet(self) -> bool:
        return False

    def is_verbose(self) -> bool:
        return False

    def is_very_verbose(self) -> bool:
        return False

    def is_debug(self) -> bool:
        return False

    def writeln(self, *args, **kwargs):
        pass

    def write(self, *args, **kwargs):
        pass

    def new_line(self, *args, **kwargs):
        pass
