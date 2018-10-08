from poetry.packages import Package
from poetry.utils.env import Env

from .repository import Repository


class InstalledRepository(Repository):
    @classmethod
    def load(cls, env):  # type: (Env) -> InstalledRepository
        """
        Load installed packages.

        For now, it uses the pip "freeze" command.
        """
        repo = cls()

        freeze_output = env.run("pip", "freeze")
        for line in freeze_output.split("\n"):
            if "==" in line:
                name, version = line.split("==")
                repo.add_package(Package(name, version, version))

        return repo
