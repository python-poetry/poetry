from .command import Command


class CheckCommand(Command):
    """
    Checks the validity of the <comment>pyproject.toml</comment> file.

    check
    """

    def handle(self):
        # Load poetry and display errors, if any
        check_result = self.poetry.check(self.poetry.local_config, strict=True)
        if not check_result["errors"] and not check_result["warnings"]:
            self.info("All set!")

            return 0

        for error in check_result["errors"]:
            self.error("Error: {}".format(error))

        for error in check_result["warnings"]:
            self.line("<warning>Warning: {}</warning>".format(error))

        return 1
