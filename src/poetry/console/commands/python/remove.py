from __future__ import annotations

import shutil

from typing import TYPE_CHECKING
from typing import ClassVar

from cleo.helpers import argument
from cleo.helpers import option
from poetry.core.constraints.version.version import Version
from poetry.core.version.exceptions import InvalidVersionError

from poetry.console.commands.command import Command
from poetry.console.commands.python import get_request_title
from poetry.utils.env.python.providers import PoetryPythonPathProvider


if TYPE_CHECKING:
    from cleo.io.inputs.argument import Argument
    from cleo.io.inputs.option import Option
    from cleo.io.io import IO


class PythonRemoveCommand(Command):
    name = "python remove"

    arguments: ClassVar[list[Argument]] = [
        argument("python", "The python version to remove.", multiple=True)
    ]
    options: ClassVar[list[Option]] = [
        option(
            "free-threaded", "t", "Use free-threaded version if available.", flag=True
        ),
        option(
            "implementation",
            "i",
            "Python implementation to use. (cpython, pypy)",
            flag=False,
            default="cpython",
        ),
    ]

    description = (
        "Remove the specified Python version if managed by Poetry."
        " (<warning>experimental feature</warning>)"
    )

    @staticmethod
    def remove_python_installation(
        request: str, implementation: str, free_threaded: bool, io: IO
    ) -> int:
        if request.endswith("t"):
            free_threaded = True
            request = request[:-1]
        try:
            version = Version.parse(request)
        except (ValueError, InvalidVersionError):
            io.write_error_line(
                f"<error>Invalid Python version requested <b>{request}</></error>"
            )
            return 1

        if version.minor is None or version.patch is None:
            io.write_error_line(
                f"<error>Invalid Python version requested <b>{request}</></error>\n"
            )
            io.write_error_line(
                "You need to provide an exact Python version in the format <c1>X.Y.Z</> to be removed.\n\n"
                "You can use <c1>poetry python list -m</> to list installed Poetry managed Python versions."
            )

            return 1

        request_title = get_request_title(request, implementation, free_threaded)
        path = PoetryPythonPathProvider.installation_dir(
            version, implementation, free_threaded
        )

        if path.exists():
            if io.is_verbose():
                io.write_line(f"Installation path: {path}")

            io.write(f"Removing installation {request_title} ... ")

            try:
                shutil.rmtree(path)
            except OSError as e:
                io.write("<fg=red>Failed</>\n")

                if io.is_verbose():
                    io.write_line(f"Failed to remove directory: {e}")

            io.write("<fg=green>Done</>\n")
        else:
            io.write_line(f"No installation was found at {path}.")

        return 0

    def handle(self) -> int:
        implementation = self.option("implementation").lower()
        free_threaded = self.option("free-threaded")

        result = 0

        for request in self.argument("python"):
            result += self.remove_python_installation(
                request, implementation, free_threaded, self.io
            )

        return result
