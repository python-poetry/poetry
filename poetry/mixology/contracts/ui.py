import sys


class UI:

    def __init__(self, debug=False):
        self._debug = debug

    @property
    def output(self):
        return sys.stdout

    @property
    def progress_rate(self) -> float:
        return 0.33

    def is_debugging(self) -> bool:
        return self._debug

    def indicate_progress(self) -> None:
        self.output.write('.')

    def before_resolution(self) -> None:
        self.output.write('Resolving dependencies...\n')

    def after_resolution(self) -> None:
        self.output.write('')

    def debug(self, message, depth) -> None:
        if self.is_debugging():
            debug_info = str(message)
            debug_info = '\n'.join([
                ':{}: {}'.format(str(depth).rjust(4), s)
                for s in debug_info.split('\n')
            ]) + '\n'

            self.output.write(debug_info)
