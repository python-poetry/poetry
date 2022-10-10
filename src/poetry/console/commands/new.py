from __future__ import annotations

import sys

from contextlib import suppress
from typing import TYPE_CHECKING

from cleo.helpers import argument
from cleo.helpers import option

from poetry.console.commands.command import Command
from poetry.utils.requirements import determine_requirements_from_list
from poetry.utils.requirements import format_requirements


if TYPE_CHECKING:
    from poetry.repositories import Pool
    from poetry.utils.requirements import Requirements


class NewCommand(Command):
    name = "new"
    description = "Creates a new Python project at <path>."

    arguments = [argument("path", "The path to create the project at.")]
    options = [
        option("name", None, "Set the resulting package name.", flag=False),
        option("description", None, "Description of the package.", flag=False),
        option("package-version", None, "Set the version of the package.", flag=False),
        option("author", None, "Author name of the package.", flag=False),
        option("python", None, "Compatible Python versions.", flag=False),
        option(
            "dependency",
            None,
            "Package to require, with an optional version constraint, "
            "e.g. requests:^2.10.0 or requests=2.11.1.",
            flag=False,
            multiple=True,
        ),
        option("license", "License of the package.", flag=False),
        option("src", None, "Use the src layout for the project."),
        option(
            "readme",
            None,
            "Specify the readme file format. One of md (default) or rst",
            flag=False,
        ),
    ]

    def __init__(self) -> None:
        super().__init__()

        self._pool: Pool | None = None

    def handle(self) -> int:
        from pathlib import Path

        from poetry.core.vcs.git import GitConfig

        from poetry.layouts import layout
        from poetry.utils.env import SystemEnv

        if self.option("src"):
            layout_cls = layout("src")
        else:
            layout_cls = layout("standard")

        path = Path(self.argument("path"))
        if not path.is_absolute():
            # we do not use resolve here due to compatibility issues
            # for path.resolve(strict=False)
            path = Path.cwd().joinpath(path)

        name = self.option("name")
        if not name:
            name = path.name

        description = self.option("description") or ""
        license = self.option("license") or ""
        version = self.option("package-version") or "0.1.0"

        if path.exists() and list(path.glob("*")):
            # Directory is not empty. Aborting.
            raise RuntimeError(
                f"Destination <fg=yellow>{path}</> exists and is not empty"
            )

        readme_format = self.option("readme") or "md"

        config = GitConfig()
        author = self.option("author")
        if not author and config.get("user.name"):
            author = config["user.name"]
            author_email = config.get("user.email")
            if author_email:
                author += f" <{author_email}>"

        current_env = SystemEnv(Path(sys.executable))

        python = self.option("python")
        if not python:
            python = "^" + ".".join(str(v) for v in current_env.version_info[:2])

        requirements: Requirements = {}
        if self.option("dependency"):
            requirements = format_requirements(
                determine_requirements_from_list(
                    self, self._get_pool(), self.option("dependency")
                )
            )

        layout_ = layout_cls(
            name,
            version,
            description=description,
            author=author,
            license=license,
            python=python,
            dependencies=requirements,
            readme_format=readme_format,
        )
        layout_.create(path)

        path = path.resolve()

        with suppress(ValueError):
            path = path.relative_to(Path.cwd())

        self.line(
            f"Created package <info>{layout_._package_name}</> in"
            f" <fg=blue>{path.as_posix()}</>"
        )

        return 0

    def _get_pool(self) -> Pool:
        from poetry.repositories import Pool
        from poetry.repositories.pypi_repository import PyPiRepository

        if self._pool is None:
            self._pool = Pool()
            self._pool.add_repository(PyPiRepository())

        return self._pool
