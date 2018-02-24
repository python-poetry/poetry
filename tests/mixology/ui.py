import sys

from io import StringIO

from poetry.mixology.contracts import UI as BaseUI


class UI(BaseUI):

    def __init__(self, debug=False):
        super(UI, self).__init__(debug)

        self._output = None

    @property
    def output(self):
        if self._output is None:
            if self.debug:
                self._output = sys.stderr
            else:
                self._output = StringIO()

        return self._output
