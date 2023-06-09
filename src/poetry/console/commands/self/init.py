from __future__ import annotations

from pathlib import Path

from cleo.helpers import option

from poetry.console.commands.self.self_command import SelfCommand


class SelfInitCommand(SelfCommand):
    name = "self init"
    description = """\
Initializes a local .poetry directory to be used instead of the global poetry \
configuration.\
"""
    options = [
        option(
            "project-dir",
            None,
            (
                "The directory containing a pyproject.toml file to which the .poetry   "
                "         directory will be added."
            ),
            flag=False,
            default=None,
        ),
    ]
    help = """\
The <c1>self init</c1> command creates and initializes a .poetry directory that\
contains poetry configuration specific for the project directory instead of using the\
global poetry configuration.
"""

    loggers = ["poetry.repositories.pypi_repository", "poetry.inspection.info"]

    def __init__(self) -> None:
        self._system_pyproject = super().system_pyproject
        super().__init__()

    def handle(self) -> int:
        project_dir = self.option("project-dir")
        if project_dir is None:
            project_dir = Path.cwd()
        self._system_pyproject = Path(project_dir) / ".poetry" / "pyproject.toml"
        if self.system_pyproject.exists():
            self.line(f"Poetry settings already exist for project {project_dir}")
            self.line_error("\nNo changes were applied.")
            return 1

        self.line(f"Initialising poetry settings for project {project_dir}")
        self.system_pyproject.parent.mkdir(parents=True, exist_ok=True)
        self.reset_poetry()
        return 0

    @property
    def system_pyproject(self) -> Path:
        return self._system_pyproject
