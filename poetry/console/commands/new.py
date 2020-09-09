import sys

from cleo import argument
from cleo import option

from poetry.utils.helpers import module_name
from poetry.vcs.git import GitConfig

from .command import Command


class NewCommand(Command):

    name = "new"
    description = "Creates a new Python project at <path>."

    arguments = [argument("path", "The path to create the project at.")]

    _config = GitConfig()

    options = [
        option("name", None, "Set the resulting package name.", flag=False),
        option(
            "author-name",
            None,
            "Author name of the package.",
            flag=False,
            default=_config.get("user.name"),
        ),
        option(
            "author-email",
            None,
            "Author email of the package.",
            flag=False,
            default=_config.get("user.email"),
        ),
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

        author = None
        author_name = self.option("author-name")
        author_email = self.option("author-email")

        if bool(author_email) != bool(author_name):
            raise ValueError(
                "`--author-name` and `--author-email` must either both be defined or undefined. "
                "If one is defined, either by passing the CLI option or by having a defined "
                "default value (see `poetry new --help` for default values), the other must also "
                "be defined."
            )
        elif author_name:
            author = "{name} <{email}>".format(name=author_name, email=author_email)

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
