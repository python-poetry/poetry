import os
import pkginfo

from pkginfo.distribution import HEADER_ATTRS
from pkginfo.distribution import HEADER_ATTRS_2_0

from poetry.io import NullIO
from poetry.utils._compat import Path
from poetry.utils._compat import decode
from poetry.utils.helpers import parse_requires
from poetry.utils.toml_file import TomlFile
from poetry.utils.venv import NullVenv
from poetry.utils.venv import Venv

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
        develop=False,  # type: bool
    ):
        from . import dependency_from_pep_508
        from .package import Package

        self._path = path
        self._base = base
        self._full_path = path
        self._develop = develop

        if self._base and not self._path.is_absolute():
            self._full_path = self._base / self._path

        if not self._full_path.exists():
            raise ValueError("Directory {} does not exist".format(self._path))

        if self._full_path.is_file():
            raise ValueError("{} is a file, expected a directory".format(self._path))

        # Checking content to dertermine actions
        setup = self._full_path / "setup.py"
        pyproject = TomlFile(self._full_path / "pyproject.toml")
        has_poetry = False
        if pyproject.exists():
            pyproject_content = pyproject.read()
            has_poetry = (
                "tool" in pyproject_content and "poetry" in pyproject_content["tool"]
            )

        if not setup.exists() and not has_poetry:
            raise ValueError(
                "Directory {} does not seem to be a Python package".format(
                    self._full_path
                )
            )

        if has_poetry:
            from poetry.masonry.builders import SdistBuilder
            from poetry.poetry import Poetry

            poetry = Poetry.create(self._full_path)
            builder = SdistBuilder(poetry, NullVenv(), NullIO())

            with setup.open("w") as f:
                f.write(decode(builder.build_setup()))

            package = poetry.package
            self._package = Package(package.pretty_name, package.version)
            self._package.requires += package.requires
            self._package.dev_requires += package.dev_requires
            self._package.extras = package.extras
            self._package.python_versions = package.python_versions
            self._package.platform = package.platform
        else:
            # Execute egg_info
            current_dir = os.getcwd()
            os.chdir(str(self._full_path))

            try:
                cwd = base
                venv = Venv.create(NullIO(), cwd=cwd)
                venv.run("python", "setup.py", "egg_info")
            finally:
                os.chdir(current_dir)

            egg_info = list(self._full_path.glob("*.egg-info"))[0]

            meta = pkginfo.UnpackedSDist(str(egg_info))

            if meta.requires_dist:
                reqs = list(meta.requires_dist)
            else:
                reqs = []
                requires = egg_info / "requires.txt"
                if requires.exists():
                    with requires.open() as f:
                        reqs = parse_requires(f.read())

            package = Package(meta.name, meta.version)
            package.description = meta.summary

            for req in reqs:
                package.requires.append(dependency_from_pep_508(req))

            if meta.requires_python:
                package.python_versions = meta.requires_python

            if meta.platforms:
                platforms = [p for p in meta.platforms if p.lower() != "unknown"]
                if platforms:
                    package.platform = " || ".join(platforms)

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

    def is_directory(self):
        return True
