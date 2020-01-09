import logging
import os
import tarfile
import zipfile

from typing import Dict
from typing import List
from typing import Union

import pkginfo

from requests import get

from ._compat import Path
from .helpers import parse_requires
from .setup_reader import SetupReader
from .toml_file import TomlFile


logger = logging.getLogger(__name__)


class Inspector:
    """
    A class to download and inspect remote packages.
    """

    @classmethod
    def download(cls, url, dest):  # type: (str, Path) -> None
        r = get(url, stream=True)
        r.raise_for_status()

        with open(str(dest), "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

    def inspect(self, file_path):  # type: (Path) -> Dict[str, Union[str, List[str]]]
        if file_path.suffix == ".whl":
            return self.inspect_wheel(file_path)

        return self.inspect_sdist(file_path)

    def inspect_wheel(
        self, file_path
    ):  # type: (Path) -> Dict[str, Union[str, List[str]]]
        info = {
            "name": "",
            "version": "",
            "summary": "",
            "requires_python": None,
            "requires_dist": [],
        }

        try:
            meta = pkginfo.Wheel(str(file_path))
        except ValueError:
            # Unable to determine dependencies
            # Assume none
            return info

        if meta.name:
            info["name"] = meta.name

        if meta.version:
            info["version"] = meta.version

        if meta.summary:
            info["summary"] = meta.summary or ""

        info["requires_python"] = meta.requires_python

        if meta.requires_dist:
            info["requires_dist"] = meta.requires_dist

        return info

    def inspect_sdist(
        self, file_path
    ):  # type: (Path) -> Dict[str, Union[str, List[str]]]
        info = {
            "name": "",
            "version": "",
            "summary": "",
            "requires_python": None,
            "requires_dist": None,
        }

        try:
            meta = pkginfo.SDist(str(file_path))
            if meta.name:
                info["name"] = meta.name

            if meta.version:
                info["version"] = meta.version

            if meta.summary:
                info["summary"] = meta.summary

            if meta.requires_python:
                info["requires_python"] = meta.requires_python

            if meta.requires_dist:
                info["requires_dist"] = list(meta.requires_dist)

                return info
        except ValueError:
            # Unable to determine dependencies
            # We pass and go deeper
            pass

        # Still not dependencies found
        # So, we unpack and introspect
        suffix = file_path.suffix
        if suffix == ".zip":
            tar = zipfile.ZipFile(str(file_path))
        else:
            if suffix == ".bz2":
                suffixes = file_path.suffixes
                if len(suffixes) > 1 and suffixes[-2] == ".tar":
                    suffix = ".tar.bz2"
            else:
                suffix = ".tar.gz"

            tar = tarfile.open(str(file_path))

        try:
            tar.extractall(os.path.join(str(file_path.parent), "unpacked"))
        finally:
            tar.close()

        unpacked = file_path.parent / "unpacked"
        elements = list(unpacked.glob("*"))
        if len(elements) == 1 and elements[0].is_dir():
            sdist_dir = elements[0]
        else:
            sdist_dir = unpacked / file_path.name.rstrip(suffix)

        pyproject = TomlFile(sdist_dir / "pyproject.toml")
        if pyproject.exists():
            from poetry.factory import Factory

            pyproject_content = pyproject.read()
            if "tool" in pyproject_content and "poetry" in pyproject_content["tool"]:
                package = Factory().create_poetry(sdist_dir).package
                return {
                    "name": package.name,
                    "version": package.version.text,
                    "summary": package.description,
                    "requires_dist": [dep.to_pep_508() for dep in package.requires],
                    "requires_python": package.python_versions,
                }

        # Checking for .egg-info at root
        eggs = list(sdist_dir.glob("*.egg-info"))
        if eggs:
            egg_info = eggs[0]

            requires = egg_info / "requires.txt"
            if requires.exists():
                with requires.open(encoding="utf-8") as f:
                    info["requires_dist"] = parse_requires(f.read())

                    return info

        # Searching for .egg-info in sub directories
        eggs = list(sdist_dir.glob("**/*.egg-info"))
        if eggs:
            egg_info = eggs[0]

            requires = egg_info / "requires.txt"
            if requires.exists():
                with requires.open(encoding="utf-8") as f:
                    info["requires_dist"] = parse_requires(f.read())

                    return info

        # Still nothing, try reading (without executing it)
        # the setup.py file.
        try:
            setup_info = self._inspect_sdist_with_setup(sdist_dir)

            for key, value in info.items():
                if value:
                    continue

                info[key] = setup_info[key]

            return info
        except Exception as e:
            logger.warning(
                "An error occurred when reading setup.py or setup.cfg: {}".format(
                    str(e)
                )
            )
            return info

    def _inspect_sdist_with_setup(
        self, sdist_dir
    ):  # type: (Path) -> Dict[str, Union[str, List[str]]]
        info = {
            "name": None,
            "version": None,
            "summary": "",
            "requires_python": None,
            "requires_dist": None,
        }

        result = SetupReader.read_from_directory(sdist_dir)
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

        info["name"] = result["name"]
        info["version"] = result["version"]
        info["requires_dist"] = parse_requires(requires)
        info["requires_python"] = result["python_requires"]

        return info
