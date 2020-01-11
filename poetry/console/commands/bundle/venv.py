from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from cleo.helpers import argument
from cleo.helpers import option

from .bundle_command import BundleCommand


if TYPE_CHECKING:
    from poetry.bundle.venv_bundler import VenvBundler  # noqa


class BundleVenvCommand(BundleCommand):

    name = "bundle venv"
    description = "Bundle the current project into a virtual environment"

    arguments = [
        argument("path", "The path to the virtual environment to bundle into."),
    ]

    options = [
        option(
            "python",
            "p",
            "The Python executable to use to create the virtual environment. "
            "Defaults to the current Python executable",
            flag=False,
            value_required=True,
        ),
        option(
            "clear",
            None,
            "Clear the existing virtual environment if it exists. ",
            flag=True,
        ),
    ]

    def handle(self) -> int:
        path = Path(self.argument("path"))
        executable = self.option("python")

        bundler = cast("VenvBundler", self._bundler_manager.bundler("venv"))

        self.line("")

        return int(
            not bundler.bundle(
                self.poetry,
                self._io,
                path,
                executable=executable,
                remove=self.option("clear"),
            )
        )
