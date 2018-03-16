import jsonschema

from .command import Command


class CheckCommand(Command):
    """
    Checks the validity of the <comment>pyproject.toml</comment> file.

    check
    """

    def handle(self):
        # Load poetry and display errors, if any
        _ = self.poetry

        self.info('All set!')
