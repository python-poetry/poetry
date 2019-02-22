from pkginfo.distribution import HEADER_ATTRS
from pkginfo.distribution import HEADER_ATTRS_2_0

from poetry.utils._compat import Path
from poetry.utils.toml_file import TomlFile

from .dependency import Dependency

# Patching pkginfo to support Metadata version 2.1 (PEP 566)
HEADER_ATTRS.update(
    {"2.1": HEADER_ATTRS_2_0 + (("Provides-Extra", "provides_extra", True),)}
)


class DirectoryDependency(Dependency):
    def __init__(
        self,
        name,
        path,  # type: Path
        category="main",  # type: str
        optional=False,  # type: bool
        base=None,  # type: Path
        develop=True,  # type: bool
    ):
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

        # Checking content to determine actions
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

        super(DirectoryDependency, self).__init__(
            name, "*", category=category, optional=optional, allows_prereleases=True
        )

    @property
    def path(self):
        return self._path

    @property
    def full_path(self):
        return self._full_path.resolve()

    @property
    def base(self):
        return self._base

    @property
    def develop(self):
        return self._develop

    def supports_poetry(self):
        return self._supports_poetry

    def is_directory(self):
        return True
