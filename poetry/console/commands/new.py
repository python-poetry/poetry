import sys

from cleo import argument
from cleo import option

from poetry.utils.helpers import module_name

from .command import Command


class NewCommand(Command):

    name = "new"
    description = "Creates a new Python project at <path>."

    arguments = [argument("path", "The path to create the project at.")]
    options = [
        option("name", None, "Set the resulting package name.", flag=False),
        option("src", None, "Use the src layout for the project."),
    ]

    def handle(self):
        from poetry.core.semver import parse_constraint
        from poetry.core.vcs.git import GitConfig
        from poetry.layouts import layout
        from poetry.utils._compat import Path
        from poetry.utils.env import SystemEnv

        if self.option("src"):
            layout_ = layout("src")
        else:
            layout_ = layout("standard")

        path = Path.cwd() / Path(self.argument("path"))
        name = self.option("name")
        if not name:
            name = path.name

        if path.exists():
            if list(path.glob("*")):
                # Directory is not empty. Aborting.
                raise RuntimeError(
                    "Destination <fg=yellow>{}</> "
                    "exists and is not empty".format(path)
                )

        readme_format = "rst"

        config = GitConfig()
        author = None
        if config.get("user.name"):
            author = config["user.name"]
            author_email = config.get("user.email")
            if author_email:
                author += " <{}>".format(author_email)

        current_env = SystemEnv(Path(sys.executable))
        default_python = "^{}".format(
            ".".join(str(v) for v in current_env.version_info[:2])
        )

        dev_dependencies = {}
        python_constraint = parse_constraint(default_python)
        if parse_constraint("<3.5").allows_any(python_constraint):
            dev_dependencies["pytest"] = "^4.6"
        if parse_constraint(">=3.5").allows_all(python_constraint):
            dev_dependencies["pytest"] = "^5.2"

        layout_ = layout_(
            name,
            "0.1.0",
            author=author,
            readme_format=readme_format,
            python=default_python,
            dev_dependencies=dev_dependencies,
        )
        layout_.create(path)

        self.line(
            "Created package <info>{}</> in <fg=blue>{}</>".format(
                module_name(name), path.relative_to(Path.cwd())
            )
        )
