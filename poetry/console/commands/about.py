from .command import Command


class AboutCommand(Command):
    """
    Short information about Poetry.

    about
    """

    def handle(self):
        self.line(
            """<info>Poetry - Package Management for Python</info>

<comment>Poetry is a dependency manager tracking local dependencies of your projects and libraries.
See <fg=blue>https://github.com/sdispater/poetry</> for more information.</comment>
"""
        )
