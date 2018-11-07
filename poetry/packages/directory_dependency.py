import glob
import os
import pkginfo

from pkginfo.distribution import HEADER_ATTRS
from pkginfo.distribution import HEADER_ATTRS_2_0

from poetry.io import NullIO
from poetry.utils._compat import PY35
from poetry.utils._compat import Path
from poetry.utils.helpers import parse_requires
from poetry.utils.toml_file import TomlFile
from poetry.utils.env import Env
from poetry.utils.env import EnvCommandError
from poetry.utils.setup_reader import SetupReader

from .dependency import Dependency

# Patching pkginfo to support Metadata version 2.1 (PEP 566)
HEADER_ATTRS.update(
    {"2.1": HEADER_ATTRS_2_0 + (("Provides-Extra", "provides_extra", True),)}
)


class DirectoryDependency(Dependency):
    def __init__(
        self,
        path,  # type: Path
        category="main",  # type: str
        optional=False,  # type: bool
        base=None,  # type: Path
        develop=True,  # type: bool
    ):
        from . import dependency_from_pep_508
        from .package import Package

        self._path = path
        self._base = base
        self._full_path = path
        self._develop = develop
        self._supports_poetry = False

        if self._base and not self._path.is_absolute():
            self._full_path = self._base / self._path

        if not self._full_path.exists():
            raise ValueError("Directory {} does not exist".format(self._path))

        if self._full_path.is_file():
            raise ValueError("{} is a file, expected a directory".format(self._path))

        # Checking content to dertermine actions
        setup = self._full_path / "setup.py"
        pyproject = TomlFile(self._full_path / "pyproject.toml")
        if pyproject.exists():
            pyproject_content = pyproject.read()
            self._supports_poetry = (
                "tool" in pyproject_content and "poetry" in pyproject_content["tool"]
            )

        if not setup.exists() and not self._supports_poetry:
            raise ValueError(
                "Directory {} does not seem to be a Python package".format(
                    self._full_path
                )
            )

        if self._supports_poetry:
            from poetry.poetry import Poetry

            poetry = Poetry.create(self._full_path)

            package = poetry.package
            self._package = Package(package.pretty_name, package.version)
            self._package.requires += package.requires
            self._package.dev_requires += package.dev_requires
            self._package.extras = package.extras
            self._package.python_versions = package.python_versions
        else:
            # Execute egg_info
            current_dir = os.getcwd()
            os.chdir(str(self._full_path))

            try:
                cwd = base
                venv = Env.get(NullIO(), cwd=cwd)
                venv.run("python", "setup.py", "egg_info")
            except EnvCommandError:
                result = SetupReader.read_from_directory(self._full_path)
                if not result["name"]:
                    # The name could not be determined
                    # so we raise an error since it is mandatory
                    raise RuntimeError(
                        "Unable to retrieve the package name for {}".format(path)
                    )

                if not result["version"]:
                    # The version could not be determined
                    # so we raise an error since it is mandatory
                    raise RuntimeError(
                        "Unable to retrieve the package version for {}".format(path)
                    )

                package_name = result["name"]
                package_version = result["version"]
                python_requires = result["python_requires"]
                if python_requires is None:
                    python_requires = "*"

                package_summary = ""

                requires = ""
                for dep in result["install_requires"]:
                    requires += dep + "\n"

                if result["extras_require"]:
                    requires += "\n"

                for extra_name, deps in result["extras_require"].items():
                    requires += "[{}]\n".format(extra_name)

                    for dep in deps:
                        requires += dep + "\n"

                    requires += "\n"

                reqs = parse_requires(requires)
            else:
                os.chdir(current_dir)
                # Sometimes pathlib will fail on recursive
                # symbolic links, so we need to workaround it
                # and use the glob module instead.
                # Note that this does not happen with pathlib2
                # so it's safe to use it for Python < 3.4.
                if PY35:
                    egg_info = next(
                        Path(p)
                        for p in glob.glob(
                            os.path.join(str(self._full_path), "**", "*.egg-info"),
                            recursive=True,
                        )
                    )
                else:
                    egg_info = next(self._full_path.glob("**/*.egg-info"))

                meta = pkginfo.UnpackedSDist(str(egg_info))
                package_name = meta.name
                package_version = meta.version
                package_summary = meta.summary
                python_requires = meta.requires_python

                if meta.requires_dist:
                    reqs = list(meta.requires_dist)
                else:
                    reqs = []
                    requires = egg_info / "requires.txt"
                    if requires.exists():
                        with requires.open() as f:
                            reqs = parse_requires(f.read())
            finally:
                os.chdir(current_dir)

            package = Package(package_name, package_version)
            package.description = package_summary

            for req in reqs:
                package.requires.append(dependency_from_pep_508(req))

            if python_requires:
                package.python_versions = python_requires

            self._package = package

        self._package.source_type = "directory"
        self._package.source_url = self._path.as_posix()

        super(DirectoryDependency, self).__init__(
            self._package.name,
            self._package.version,
            category=category,
            optional=optional,
            allows_prereleases=True,
        )

    @property
    def path(self):
        return self._path

    @property
    def full_path(self):
        return self._full_path.resolve()

    @property
    def package(self):
        return self._package

    @property
    def develop(self):
        return self._develop

    def supports_poetry(self):
        return self._supports_poetry

    def is_directory(self):
        return True
