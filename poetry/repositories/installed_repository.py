import itertools

from typing import Set
from typing import Union

from poetry.core.packages import Package
from poetry.core.utils.helpers import module_name
from poetry.utils._compat import Path
from poetry.utils._compat import metadata
from poetry.utils.env import Env

from .repository import Repository


_VENDORS = Path(__file__).parent.parent.joinpath("_vendor")


try:
    FileNotFoundError
except NameError:
    FileNotFoundError = OSError


class InstalledRepository(Repository):
    @classmethod
    def get_package_paths(cls, env, name):  # type: (Env, str) -> Set[Path]
        """
        Process a .pth file within the site-packages directories, and return any valid
        paths. We skip executable .pth files as there is no reliable means to do this
        without side-effects to current run-time. Mo check is made that the item refers
        to a directory rather than a file, however, in order to maintain backwards
        compatibility, we allow non-existing paths to be discovered. The latter
        behaviour is different to how Python's site-specific hook configuration works.

        Reference: https://docs.python.org/3.8/library/site.html

        :param env: The environment to search for the .pth file in.
        :param name: The name of the package to search .pth file for.
        :return: A `Set` of valid `Path` objects.
        """
        paths = set()

        # we identify the candidate pth files to check, this is done so to handle cases
        # where the pth file for foo-bar might have been installed as either foo-bar.pth or
        # foo_bar.pth (expected) in either pure or platform lib directories.
        candidates = itertools.product(
            {env.purelib, env.platlib}, {name, module_name(name)},
        )

        for lib, module in candidates:
            pth_file = lib.joinpath(module).with_suffix(".pth")
            if not pth_file.exists():
                continue

            with pth_file.open() as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith(("#", "import ", "import\t")):
                        path = Path(line)
                        if not path.is_absolute():
                            try:
                                path = lib.joinpath(path).resolve()
                            except FileNotFoundError:
                                # this is required to handle pathlib oddity on win32 python==3.5
                                path = lib.joinpath(path)
                        paths.add(path)
        return paths

    @classmethod
    def set_package_vcs_properties_from_path(
        cls, src, package
    ):  # type: (Path, Package) -> None
        from poetry.core.vcs.git import Git

        git = Git()
        revision = git.rev_parse("HEAD", src).strip()
        url = git.remote_url(src)

        package._source_type = "git"
        package._source_url = url
        package._source_reference = revision

    @classmethod
    def set_package_vcs_properties(cls, package, env):  # type: (Package, Env) -> None
        src = env.path / "src" / package.name
        cls.set_package_vcs_properties_from_path(src, package)

    @classmethod
    def is_vcs_package(cls, package, env):  # type: (Union[Path, Package], Env) -> bool
        # A VCS dependency should have been installed
        # in the src directory.
        src = env.path / "src"
        if isinstance(package, Package):
            return src.joinpath(package.name).is_dir()

        try:
            package.relative_to(env.path / "src")
        except ValueError:
            return False
        else:
            return True

    @classmethod
    def load(cls, env):  # type: (Env) -> InstalledRepository
        """
        Load installed packages.
        """
        repo = cls()
        seen = set()

        for entry in reversed(env.sys_path):
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
                    path.relative_to(_VENDORS)
                except ValueError:
                    pass
                else:
                    continue

                seen.add(package.name)

                repo.add_package(package)

                is_standard_package = env.is_path_relative_to_lib(path)

                if is_standard_package:
                    if path.name.endswith(".dist-info"):
                        paths = cls.get_package_paths(env=env, name=package.pretty_name)
                        if paths:
                            is_editable_package = False
                            for src in paths:
                                if cls.is_vcs_package(src, env):
                                    cls.set_package_vcs_properties(package, env)
                                    break

                                if not (
                                    is_editable_package
                                    or env.is_path_relative_to_lib(src)
                                ):
                                    is_editable_package = True
                            else:
                                # TODO: handle multiple source directories?
                                if is_editable_package:
                                    package._source_type = "directory"
                                    package._source_url = paths.pop().as_posix()
                    continue

                if cls.is_vcs_package(path, env):
                    cls.set_package_vcs_properties(package, env)
                else:
                    # If not, it's a path dependency
                    package._source_type = "directory"
                    package._source_url = str(path.parent)

        return repo
