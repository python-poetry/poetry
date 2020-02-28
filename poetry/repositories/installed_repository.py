from poetry import _CURRENT_VENDOR
from poetry.packages import Package
from poetry.utils._compat import Path
from poetry.utils._compat import metadata
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
        seen = set()

        for entry in env.sys_path:
            for distribution in sorted(
                metadata.distributions(path=[entry]), key=lambda d: str(d._path),
            ):
                name = distribution.metadata["name"]
                path = Path(str(distribution._path))
                version = distribution.metadata["version"]
                package = Package(name, version, version)
                package.description = distribution.metadata.get("summary", "")

                if package.name in seen:
                    continue

                try:
                    path.relative_to(_CURRENT_VENDOR)
                except ValueError:
                    pass
                else:
                    continue

                seen.add(package.name)

                repo.add_package(package)

                is_standard_package = True
                try:
                    path.relative_to(env.site_packages)
                except ValueError:
                    is_standard_package = False

                if is_standard_package:
                    continue

                src_path = env.path / "src"

                # A VCS dependency should have been installed
                # in the src directory. If not, it's a path dependency
                try:
                    path.relative_to(src_path)

                    from poetry.vcs.git import Git

                    git = Git()
                    revision = git.rev_parse("HEAD", src_path / package.name).strip()
                    url = git.remote_url(src_path / package.name)

                    package.source_type = "git"
                    package.source_url = url
                    package.source_reference = revision
                except ValueError:
                    package.source_type = "directory"
                    package.source_url = str(path.parent)

        return repo
