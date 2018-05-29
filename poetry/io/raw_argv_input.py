import sys

from cleo.inputs import ArgvInput


class RawArgvInput(ArgvInput):
    def parse(self):
        self._parsed = self._tokens
        while True:
            try:
                token = self._parsed.pop(0)
            except IndexError:
                break

            self.parse_argument(token)
