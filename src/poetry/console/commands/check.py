from __future__ import annotations

from pathlib import Path

from poetry.console.commands.command import Command


class CheckCommand(Command):
    name = "check"
    description = "Checks the validity of the <comment>pyproject.toml</comment> file."

    def handle(self) -> int:
        from poetry.core.pyproject.toml import PyProjectTOML

        from poetry.factory import Factory

        # Load poetry config and display errors, if any
        poetry_file = Factory.locate(Path.cwd())
        config = PyProjectTOML(poetry_file).poetry_config
        check_result = Factory.validate(config, strict=True)
        if not check_result["errors"] and not check_result["warnings"]:
            self.info("All set!")

            return 0

        for error in check_result["errors"]:
            self.line_error(f"<error>Error: {error}</error>")

        for error in check_result["warnings"]:
            self.line_error(f"<warning>Warning: {error}</warning>")

        return 1
