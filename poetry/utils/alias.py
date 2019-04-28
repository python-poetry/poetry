import tomlkit

from typing import Dict

from poetry.config import Config
from poetry.locations import CACHE_DIR
from poetry.utils._compat import Path
from poetry.utils.toml_file import TomlFile


class AliasManager(object):
    """
    Project aliases manager.
    """

    def __init__(self, config=None):  # type: (Config) -> None
        if config is None:
            config = Config.create("config.toml")

        venv_path = config.setting("settings.virtualenvs.path")
        if venv_path is None:
            venv_path = Path(CACHE_DIR) / "virtualenvs"
        else:
            venv_path = Path(venv_path)

        self.aliases_file = TomlFile(venv_path / "aliases.toml")
        self.aliases = tomlkit.document()

        if self.aliases_file.exists():
            self.aliases = self.aliases_file.read()

    def list(self):  # type: () -> Dict[str, str]
        """
        Return a list of all project alias definitions.
        """
        return {name: project for name, project in self.aliases.items()}

    def get_alias(self, project_path):  # type: (Path) -> str
        """
        Get the alias for a given project.
        """
        project_dirname = str(project_path)

        for n, p in self.aliases.items():
            if p == project_dirname:
                return n

        raise AliasCommandError("No alias defined for the project")

    def get_project(self, name):  # type: (str) -> Path
        """
        Get the project path for a given alias.
        """
        try:
            project_dirname = self.aliases[name]
        except KeyError:
            raise AliasCommandError("Unknown project alias: {}".format(name))

        return Path(project_dirname)

    def remove(self, project_path):  # type: (Path) -> None
        """
        Remove aliase(es) for a project.
        """
        project_dirname = str(project_path)

        for n, p in self.aliases.items():
            if p == project_dirname:
                del self.aliases[n]

        self.aliases_file.write(self.aliases)

    def set(self, project_path, name):  # type: (Path, str) -> None
        """
        Set an alias for a project.
        """
        project_dirname = str(project_path)

        # Check the the alias isn't already used for a different project
        existing_project = self.aliases.get(name, None)

        if existing_project is not None and existing_project != project_dirname:
            raise AliasCommandError(
                'Alias "{}" already exists for project {}'.format(
                    name, existing_project
                )
            )

        # Add alias to the aliases file
        self.remove(project_path)
        self.aliases[name] = project_dirname
        self.aliases_file.write(self.aliases)


class AliasCommandError(Exception):

    pass
