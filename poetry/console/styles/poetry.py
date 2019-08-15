from cleo.styles import CleoStyle
from cleo.styles import OutputStyle


class PoetryStyle(CleoStyle):
    def __init__(self, i, o):
        super(PoetryStyle, self).__init__(i, o)

        self.output.get_formatter().add_style("error", "red")
        self.output.get_formatter().add_style("warning", "yellow")
        self.output.get_formatter().add_style("question", "blue")
        self.output.get_formatter().add_style("comment", "cyan")
        self.output.get_formatter().add_style("debug", "black", options=["bold"])

    def writeln(
        self,
        messages,
        type=OutputStyle.OUTPUT_NORMAL,
        verbosity=OutputStyle.VERBOSITY_NORMAL,
    ):
        if self.output.verbosity >= verbosity:
            super(PoetryStyle, self).writeln(messages, type=type)

    def write(
        self,
        messages,
        newline=False,
        type=OutputStyle.OUTPUT_NORMAL,
        verbosity=OutputStyle.VERBOSITY_NORMAL,
    ):
        if self.output.verbosity >= verbosity:
            super(PoetryStyle, self).write(messages, newline=newline, type=type)
