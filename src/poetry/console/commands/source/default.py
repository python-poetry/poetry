from __future__ import annotations

from cleo.helpers import option

from poetry.console.commands.command import Command


class SourceDefaultCommand(Command):
    name = "source default"
    description = "Enable or disable the implicit default source PyPI for the project."

    options = [
        option("enable-pypi", None, "Enable PyPI as implicit default source."),
        option("disable-pypi", None, "Disable PyPI as implicit default source."),
    ]

    def handle(self) -> int:
        enable_pypi = self.option("enable-pypi")
        disable_pypi = self.option("disable-pypi")

        if enable_pypi and disable_pypi:
            self.line_error("Cannot enable and disable PyPI.")
            return 1

        if enable_pypi or disable_pypi:
            self.poetry.pyproject.poetry_config["default-source-pypi"] = enable_pypi
            self.poetry.pyproject.save()

        else:
            state = (
                "enabled"
                if self.poetry.pyproject.poetry_config.get("default-source-pypi", True)
                else "disabled"
            )
            self.line(f"PyPI is {state} as implicit default source.")

        return 0
