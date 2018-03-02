from cleo.styles import CleoStyle


class PoetryStyle(CleoStyle):

    def __init__(self, i, o, venv):
        self._venv = venv

        super().__init__(i, o)

        self.output.get_formatter().add_style('warning', 'black', 'yellow')

    @property
    def venv(self):
        return self._venv
