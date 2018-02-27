from cleo.styles import CleoStyle


class PoetryStyle(CleoStyle):

    def __init__(self, i, o, venv):
        self._venv = venv

        super().__init__(i, o)

    @property
    def venv(self):
        return self._venv
