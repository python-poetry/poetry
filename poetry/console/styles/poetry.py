from cleo.styles import CleoStyle
from cleo.styles import OutputStyle


class PoetryStyle(CleoStyle):

    def __init__(self, i, o):
        super().__init__(i, o)

        self.output.get_formatter().add_style('warning', 'black', 'yellow')
        self.output.get_formatter().add_style('question', 'blue')

    def writeln(self, messages,
                type=OutputStyle.OUTPUT_NORMAL,
                verbosity=OutputStyle.VERBOSITY_NORMAL):
        if self.output.verbosity >= verbosity:
            super().writeln(messages, type=type)

    def write(self, messages,
              newline=False,
              type=OutputStyle.OUTPUT_NORMAL,
              verbosity=OutputStyle.VERBOSITY_NORMAL):
        if self.output.verbosity >= verbosity:
            super().write(messages, newline=newline, type=type)
