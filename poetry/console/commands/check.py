from .command import Command


class CheckCommand(Command):
    """
    Checks the validity of the <comment>pyproject.toml</comment> file.

    check
    """

    def handle(self):
        # Load poetry and display errors, if any
        self.poetry.check(self.poetry.local_config, strict=True)

        self.info("All set!")
