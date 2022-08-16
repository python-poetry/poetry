import glob
import logging
import os
import tarfile
import zipfile

from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Union

import pkginfo

from poetry.core.factory import Factory
from poetry.core.packages import Package
from poetry.core.packages import ProjectPackage
from poetry.core.packages import dependency_from_pep_508
from poetry.core.utils._compat import PY35
from poetry.core.utils._compat import Path
from poetry.core.utils.helpers import parse_requires
from poetry.core.utils.helpers import temporary_directory
from poetry.core.version.markers import InvalidMarker
from poetry.utils.env import EnvCommandError
from poetry.utils.env import EnvManager
from poetry.utils.env import VirtualEnv
from poetry.utils.setup_reader import SetupReader
from poetry.utils.toml_file import TomlFile


logger = logging.getLogger(__name__)


class PackageInfoError(ValueError):
    def __init__(self, path):  # type: (Union[Path, str]) -> None
        super(PackageInfoError, self).__init__(
            "Unable to determine package info for path: {}".format(str(path))
        )


class PackageInfo:
    def __init__(
        self,
        name=None,  # type: Optional[str]
        version=None,  # type: Optional[str]
        summary=None,  # type: Optional[str]
        platform=None,  # type: Optional[str]
        requires_dist=None,  # type: Optional[List[str]]
        requires_python=None,  # type: Optional[str]
        files=None,  # type: Optional[List[str]]
        cache_version=None,  # type: Optional[str]
    ):
        self.name = name
        self.version = version
        self.summary = summary
        self.platform = platform
        self.requires_dist = requires_dist
        self.requires_python = requires_python
        self.files = files or []
        self._cache_version = cache_version

    @property
    def cache_version(self):  # type: () -> Optional[str]
        return self._cache_version

    def update(self, other):  # type: (PackageInfo) -> PackageInfo
        self.name = other.name or self.name
        self.version = other.version or self.version
        self.summary = other.summary or self.summary
        self.platform = other.platform or self.platform
        self.requires_dist = other.requires_dist or self.requires_dist
        self.requires_python = other.requires_python or self.requires_python
        self.files = other.files or self.files
        self._cache_version = other.cache_version or self._cache_version
        return self

    def asdict(self):  # type: () -> Dict[str, Optional[Union[str, List[str]]]]
        """
        Helper method to convert package info into a dictionary used for caching.
        """
        return {
            "name": self.name,
            "version": self.version,
            "summary": self.summary,
            "platform": self.platform,
            "requires_dist": self.requires_dist,
            "requires_python": self.requires_python,
            "files": self.files,
            "_cache_version": self._cache_version,
        }

    @classmethod
    def load(
        cls, data
    ):  # type: (Dict[str, Optional[Union[str, List[str]]]]) -> PackageInfo
        """
        Helper method to load data from a dictionary produced by `PackageInfo.asdict()`.

        :param data: Data to load. This is expected to be a `dict` object output by `asdict()`.
        """
        cache_version = data.pop("_cache_version", None)
        return cls(cache_version=cache_version, **data)

    @classmethod
    def _log(cls, msg, level="info"):
        """Internal helper method to log information."""
        getattr(logger, level)("<debug>{}:</debug> {}".format(cls.__name__, msg))

    def to_package(
        self, name=None, extras=None, root_dir=None
    ):  # type: (Optional[str], Optional[List[str]], Optional[Path]) -> Package
        """
        Create a new `poetry.core.packages.package.Package` instance using metadata from this instance.

        :param name: Name to use for the package, if not specified name from this instance is used.
        :param extras: Extras to activate for this package.
        :param root_dir:  Optional root directory to use for the package. If set, dependency strings
            will be parsed relative to this directory.
        """
        name = name or self.name

        if not self.version:
            # The version could not be determined, so we raise an error since it is mandatory.
            raise RuntimeError(
                "Unable to retrieve the package version for {}".format(name)
            )

        package = Package(name=name, version=self.version)
        package.description = self.summary
        package.root_dir = root_dir
        package.python_versions = self.requires_python or "*"
        package.files = self.files

        for req in self.requires_dist or []:
            try:
                # Attempt to parse the PEP-508 requirement string
                dependency = dependency_from_pep_508(req, relative_to=root_dir)
            except InvalidMarker:
                # Invalid marker, We strip the markers hoping for the best
                req = req.split(";")[0]
                dependency = dependency_from_pep_508(req, relative_to=root_dir)
            except ValueError:
                # Likely unable to parse constraint so we skip it
                self._log(
                    "Invalid constraint ({}) found in {}-{} dependencies, "
                    "skipping".format(req, package.name, package.version),
                    level="debug",
                )
                continue

            if dependency.in_extras:
                # this dependency is required by an extra package
                for extra in dependency.in_extras:
                    if extra not in package.extras:
                        # this is the first time we encounter this extra for this package
                        package.extras[extra] = []

                    # Activate extra dependencies if specified
                    if extras and extra in extras:
                        dependency.activate()

                    package.extras[extra].append(dependency)

            if not dependency.is_optional() or dependency.is_activated():
                # we skip add only if the dependency is option and was not activated as part of an extra
                package.requires.append(dependency)

        return package

    @classmethod
    def _from_distribution(
        cls, dist
    ):  # type: (Union[pkginfo.BDist, pkginfo.SDist, pkginfo.Wheel]) -> PackageInfo
        """
        Helper method to parse package information from a `pkginfo.Distribution` instance.

        :param dist: The distribution instance to parse information from.
        """
        requirements = None

        if dist.requires_dist:
            requirements = list(dist.requires_dist)
        else:
            requires = Path(dist.filename) / "requires.txt"
            if requires.exists():
                with requires.open(encoding="utf-8") as f:
                    requirements = parse_requires(f.read())

        return cls(
            name=dist.name,
            version=dist.version,
            summary=dist.summary,
            platform=dist.supported_platforms,
            requires_dist=requirements,
            requires_python=dist.requires_python,
        )

    @classmethod
    def _from_sdist_file(cls, path):  # type: (Path) -> PackageInfo
        """
        Helper method to parse package information from an sdist file. We attempt to first inspect the
        file using `pkginfo.SDist`. If this does not provide us with package requirements, we extract the
        source and handle it as a directory.

        :param path: The sdist file to parse information from.
        """
        info = None

        try:
            info = cls._from_distribution(pkginfo.SDist(str(path)))
        except ValueError:
            # Unable to determine dependencies
            # We pass and go deeper
            pass
        else:
            if info.requires_dist is not None:
                # we successfully retrieved dependencies from sdist metadata
                return info

        # Still not dependencies found
        # So, we unpack and introspect
        suffix = path.suffix

        if suffix == ".zip":
            context = zipfile.ZipFile
        else:
            if suffix == ".bz2":
                suffixes = path.suffixes
                if len(suffixes) > 1 and suffixes[-2] == ".tar":
                    suffix = ".tar.bz2"
            else:
                suffix = ".tar.gz"

            context = tarfile.open

        with temporary_directory() as tmp:
            tmp = Path(tmp)
            with context(path.as_posix()) as archive:
                archive.extractall(tmp.as_posix())

            # a little bit of guess work to determine the directory we care about
            elements = list(tmp.glob("*"))

            if len(elements) == 1 and elements[0].is_dir():
                sdist_dir = elements[0]
            else:
                sdist_dir = tmp / path.name.rstrip(suffix)
                if not sdist_dir.is_dir():
                    sdist_dir = tmp

            # now this is an unpacked directory we know how to deal with
            new_info = cls.from_directory(path=sdist_dir)

        if not info:
            return new_info

        return info.update(new_info)

    @classmethod
    def from_setup_py(cls, path):  # type: (Union[str, Path]) -> PackageInfo
        """
        Mechanism to parse package information from a `setup.py` file. This uses the implentation
        at `poetry.utils.setup_reader.SetupReader` in order to parse the file. This is not reliable for
        complex setup files and should only attempted as a fallback.

        :param path: Path to `setup.py` file
        :return:
        """
        result = SetupReader.read_from_directory(Path(path))
        python_requires = result["python_requires"]
        if python_requires is None:
            python_requires = "*"

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

        requirements = parse_requires(requires)

        return cls(
            name=result.get("name"),
            version=result.get("version"),
            summary=result.get("description", ""),
            requires_dist=requirements or None,
            requires_python=python_requires,
        )

    @staticmethod
    def _find_dist_info(path):  # type: (Path) -> Iterator[Path]
        """
        Discover all `*.*-info` directories in a given path.

        :param path: Path to search.
        """
        pattern = "**/*.*-info"
        if PY35:
            # Sometimes pathlib will fail on recursive symbolic links, so we need to workaround it
            # and use the glob module instead. Note that this does not happen with pathlib2
            # so it's safe to use it for Python < 3.4.
            directories = glob.iglob(Path(path, pattern).as_posix(), recursive=True)
        else:
            directories = path.glob(pattern)

        for d in directories:
            yield Path(d)

    @classmethod
    def from_metadata(cls, path):  # type: (Union[str, Path]) -> Optional[PackageInfo]
        """
        Helper method to parse package information from an unpacked metadata directory.

        :param path: The metadata directory to parse information from.
        """
        path = Path(path)

        if path.suffix in {".dist-info", ".egg-info"}:
            directories = [path]
        else:
            directories = cls._find_dist_info(path=path)

        for directory in directories:
            try:
                if directory.suffix == ".egg-info":
                    dist = pkginfo.UnpackedSDist(directory.as_posix())
                elif directory.suffix == ".dist-info":
                    dist = pkginfo.Wheel(directory.as_posix())
                else:
                    continue
                break
            except ValueError:
                continue
        else:
            try:
                # handle PKG-INFO in unpacked sdist root
                dist = pkginfo.UnpackedSDist(path.as_posix())
            except ValueError:
                return

        info = cls._from_distribution(dist=dist)
        if info:
            return info

    @classmethod
    def from_package(cls, package):  # type: (Package) -> PackageInfo
        """
        Helper method to inspect a `Package` object, in order to generate package info.

        :param package: This must be a poetry package instance.
        """
        requires = {dependency.to_pep_508() for dependency in package.requires}

        for extra_requires in package.extras.values():
            for dependency in extra_requires:
                requires.add(dependency.to_pep_508())

        return cls(
            name=package.name,
            version=str(package.version),
            summary=package.description,
            platform=package.platform,
            requires_dist=list(requires),
            requires_python=package.python_versions,
            files=package.files,
        )

    @staticmethod
    def _get_poetry_package(path):  # type: (Path) -> Optional[ProjectPackage]
        pyproject = path.joinpath("pyproject.toml")
        try:
            # Note: we ignore any setup.py file at this step
            if pyproject.exists():
                # TODO: add support for handling non-poetry PEP-517 builds
                pyproject = TomlFile(pyproject)
                pyproject_content = pyproject.read()
                supports_poetry = (
                    "tool" in pyproject_content
                    and "poetry" in pyproject_content["tool"]
                )
                if supports_poetry:
                    return Factory().create_poetry(path).package
        except RuntimeError:
            pass

    @classmethod
    def from_directory(
        cls, path, allow_build=False
    ):  # type: (Union[str, Path], bool) -> PackageInfo
        """
        Generate package information from a package source directory. When `allow_build` is enabled and
        introspection of all available metadata fails, the package is attempted to be build in an isolated
        environment so as to generate required metadata.

        :param path: Path to generate package information from.
        :param allow_build: If enabled, as a fallback, build the project to gather metadata.
        """
        path = Path(path)

        current_dir = os.getcwd()

        info = cls.from_metadata(path)

        if info and info.requires_dist is not None:
            # return only if requirements are discovered
            return info

        setup_py = path.joinpath("setup.py")

        project_package = cls._get_poetry_package(path)
        if project_package:
            return cls.from_package(project_package)

        if not setup_py.exists():
            if not allow_build and info:
                # we discovered PkgInfo but no requirements were listed
                return info
            # this means we cannot do anything else here
            raise PackageInfoError(path)

        if not allow_build:
            return cls.from_setup_py(path=path)

        try:
            # TODO: replace with PEP517
            # we need to switch to the correct path in order for egg_info command to work
            os.chdir(str(path))

            # Execute egg_info
            cls._execute_setup()
        except EnvCommandError:
            cls._log(
                "Falling back to parsing setup.py file for {}".format(path), "debug"
            )
            # egg_info could not be generated, we fallback to ast parser
            return cls.from_setup_py(path=path)
        else:
            info = cls.from_metadata(path)
            if info:
                return info
        finally:
            os.chdir(current_dir)

        # if we reach here, everything has failed and all hope is lost
        raise PackageInfoError(path)

    @classmethod
    def from_sdist(cls, path):  # type: (Union[Path, pkginfo.SDist]) -> PackageInfo
        """
        Gather package information from an sdist file, packed or unpacked.

        :param path: Path to an sdist file or unpacked directory.
        """
        if path.is_file():
            return cls._from_sdist_file(path=path)

        # if we get here then it is neither an sdist instance nor a file
        # so, we assume this is an directory
        return cls.from_directory(path=path)

    @classmethod
    def from_wheel(cls, path):  # type: (Path) -> PackageInfo
        """
        Gather package information from a wheel.

        :param path: Path to wheel.
        """
        try:
            return cls._from_distribution(pkginfo.Wheel(str(path)))
        except ValueError:
            return PackageInfo()

    @classmethod
    def from_bdist(cls, path):  # type: (Path) -> PackageInfo
        """
        Gather package information from a bdist (wheel etc.).

        :param path: Path to bdist.
        """
        if isinstance(path, (pkginfo.BDist, pkginfo.Wheel)):
            cls._from_distribution(dist=path)

        if path.suffix == ".whl":
            return cls.from_wheel(path=path)

        try:
            return cls._from_distribution(pkginfo.BDist(str(path)))
        except ValueError:
            raise PackageInfoError(path)

    @classmethod
    def from_path(cls, path):  # type: (Path) -> PackageInfo
        """
        Gather package information from a given path (bdist, sdist, directory).

        :param path: Path to inspect.
        """
        try:
            return cls.from_bdist(path=path)
        except PackageInfoError:
            return cls.from_sdist(path=path)

    @classmethod
    def _execute_setup(cls):
        with temporary_directory() as tmp_dir:
            EnvManager.build_venv(tmp_dir)
            venv = VirtualEnv(Path(tmp_dir), Path(tmp_dir))
            venv.run("python", "setup.py", "egg_info")
