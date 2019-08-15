import re

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
                name, version = re.split("={2,3}", line)
                repo.add_package(Package(name, version, version))
            elif line.startswith("-e "):
                line = line[3:].strip()
                if line.startswith("git+"):
                    url = line.lstrip("git+")
                    if "@" in url:
                        url, rev = url.rsplit("@", 1)
                    else:
                        rev = "master"

                    name = url.split("/")[-1].rstrip(".git")
                    if "#egg=" in rev:
                        rev, name = rev.split("#egg=")

                    package = Package(name, "0.0.0")
                    package.source_type = "git"
                    package.source_url = url
                    package.source_reference = rev

                    repo.add_package(package)

        return repo
