from cleo.inputs import ListInput
from cleo.outputs import NullOutput

from poetry.console.styles.poetry import PoetryStyle


class NullIO(PoetryStyle):
    def __init__(self):
        super(NullIO, self).__init__(ListInput([]), NullOutput())

    def is_quiet(self):  # type: () -> bool
        return False

    def is_verbose(self):  # type: () -> bool
        return False

    def is_very_verbose(self):  # type: () -> bool
        return False

    def is_debug(self):  # type: () -> bool
        return False

    def writeln(self, *args, **kwargs):
        pass

    def write(self, *args, **kwargs):
        pass

    def new_line(self, *args, **kwargs):
        pass
