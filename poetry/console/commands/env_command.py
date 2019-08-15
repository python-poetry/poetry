from .command import Command


class EnvCommand(Command):
    def __init__(self):
        self._env = None

        super(EnvCommand, self).__init__()

    def initialize(self, i, o):
        from poetry.semver import parse_constraint
        from poetry.utils.env import Env

        super(EnvCommand, self).initialize(i, o)

        # Checking compatibility of the current environment with
        # the python dependency specified in pyproject.toml
        current_env = Env.get(self.poetry.file.parent)
        supported_python = self.poetry.package.python_constraint
        current_python = parse_constraint(
            ".".join(str(v) for v in current_env.version_info[:3])
        )

        if not supported_python.allows(current_python):
            raise RuntimeError(
                "The current Python version ({}) is not supported by the project ({})\n"
                "Please activate a compatible Python version.".format(
                    current_python, self.poetry.package.python_versions
                )
            )

        self._env = Env.create_venv(
            self.poetry.file.parent, o, self.poetry.package.name
        )

        if self._env.is_venv() and o.is_verbose():
            o.writeln("Using virtualenv: <comment>{}</>".format(self._env.path))

    @property
    def env(self):
        return self._env
