from poetry.utils.venv import Venv


class NullVenv(Venv):

    def __init__(self):
        super().__init__()

        self.executed = []

    def run(self, bin: str, *args):
        self.executed.append([bin] + list(args))

    def _bin(self, bin):
        return bin


class NullIO:

    def __init__(self):
        self._venv = NullVenv()

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
