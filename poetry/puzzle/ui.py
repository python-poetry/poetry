from cleo.styles import CleoStyle
from cleo.helpers import ProgressIndicator
from poetry.mixology.contracts import UI as BaseUI


class UI(BaseUI):

    def __init__(self, io: CleoStyle):
        self._io = io
        self._progress = None

        super().__init__(self._io.is_debug())

    @property
    def output(self):
        return self._io

    def before_resolution(self) -> None:
        self._io.write('<info>Resolving dependencies</>')

        if self.is_debugging():
            self._io.new_line()

    def indicate_progress(self):
        if not self.is_debugging():
            self._io.write('.')

    def after_resolution(self) -> None:
        self._io.new_line()

    def debug(self, message, depth) -> None:
        if self.is_debugging():
            debug_info = str(message)
            debug_info = '\n'.join([
                '<comment>:{}:</> {}'.format(str(depth).rjust(4), s)
                for s in debug_info.split('\n')
            ]) + '\n'

            self.output.write(debug_info)
