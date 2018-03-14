from cleo.inputs import ListInput
from cleo.outputs import NullOutput

from poetry.console.styles.poetry import PoetryStyle


class NullIO(PoetryStyle):

    def __init__(self):
        super().__init__(ListInput([]), NullOutput())

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
