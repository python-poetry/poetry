from typing import Set

from poetry.core.packages import Package
from poetry.utils._compat import Path
from poetry.utils._compat import metadata
from poetry.utils.env import Env

from .repository import Repository


_VENDORS = Path(__file__).parent.parent.joinpath("_vendor")


class InstalledRepository(Repository):
    @classmethod
    def get_package_paths(cls, sitedir, name):  # type: (Path, str) -> Set[Path]
        """
        Process a .pth file within the site-packages directory, and return any valid
        paths. We skip executable .pth files as there is no reliable means to do this
        without side-effects to current run-time. Mo check is made that the item refers
        to a directory rather than a file, however, in order to maintain backwards
        compatibility, we allow non-existing paths to be discovered. The latter
        behaviour is different to how Python's site-specific hook configuration works.

        Reference: https://docs.python.org/3.8/library/site.html

        :param sitedir: The site-packages directory to search for .pth file.
        :param name: The name of the package to search .pth file for.
        :return: A `Set` of valid `Path` objects.
        """
        paths = set()

        pth_file = sitedir.joinpath("{}.pth".format(name))
        if pth_file.exists():
            with pth_file.open() as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith(("#", "import ", "import\t")):
                        path = Path(line)
                        if not path.is_absolute():
                            path = sitedir.joinpath(path)
                        paths.add(path)

        return paths

    @classmethod
    def load(cls, env):  # type: (Env) -> InstalledRepository
        """
        Load installed packages.
        """
        repo = cls()
        seen = set()

        for entry in reversed(env.sys_path):
            for distribution in sorted(
                metadata.distributions(path=[entry]),
                key=lambda d: str(d._path),
            ):
                name = distribution.metadata["name"]
                path = Path(str(distribution._path))
                version = distribution.metadata["version"]
                package = Package(name, version, version)
                package.description = distribution.metadata.get("summary", "")

                if package.name in seen:
                    continue

                try:
                    path.relative_to(_VENDORS)
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
                    if path.name.endswith(".dist-info"):
                        paths = cls.get_package_paths(
                            sitedir=env.site_packages, name=package.pretty_name
                        )
                        if paths:
                            # TODO: handle multiple source directories?
                            package.source_type = "directory"
                            package.source_url = paths.pop().as_posix()

                    continue

                src_path = env.path / "src"

                # A VCS dependency should have been installed
                # in the src directory. If not, it's a path dependency
                try:
                    path.relative_to(src_path)

                    from poetry.core.vcs.git import Git

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
