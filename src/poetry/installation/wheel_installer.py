from __future__ import annotations

import logging
import os
import platform
import sys
import tempfile

from pathlib import Path
from typing import TYPE_CHECKING

from installer import install
from installer.destinations import SchemeDictionaryDestination
from installer.sources import WheelFile
from installer.sources import _WheelFileValidationError

from poetry.__version__ import __version__
from poetry.utils._compat import WINDOWS


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Collection
    from typing import BinaryIO

    from installer.records import RecordEntry
    from installer.scripts import LauncherKind
    from installer.utils import Scheme

    from poetry.utils.env import Env


class WheelDestination(SchemeDictionaryDestination):
    """ """

    def write_to_fs(
        self,
        scheme: Scheme,
        path: str,
        stream: BinaryIO,
        is_executable: bool,
    ) -> RecordEntry:
        from installer.records import Hash
        from installer.records import RecordEntry
        from installer.utils import copyfileobj_with_hashing
        from installer.utils import make_file_executable

        target_path = Path(self.scheme_dict[scheme]) / path
        if target_path.exists():
            # Contrary to the base library we don't raise an error here since it can
            # break pkgutil-style and pkg_resource-style namespace packages.
            logger.warning(f"Installing {target_path} over existing file")

        parent_folder = target_path.parent
        if not parent_folder.exists():
            # Due to the parallel installation it can happen
            # that two threads try to create the directory.
            parent_folder.mkdir(parents=True, exist_ok=True)

        with target_path.open("wb") as f:
            hash_, size = copyfileobj_with_hashing(stream, f, self.hash_algorithm)

        if is_executable:
            make_file_executable(target_path)

        return RecordEntry(path, Hash(self.hash_algorithm, hash_), size)


class WheelDestinationCopy(SchemeDictionaryDestination):
    """SchemeDictionaryDestination that copies the files with os.replace to avoid race condition"""

    def write_to_fs(
        self,
        scheme: Scheme,
        path: str,
        stream: BinaryIO,
        is_executable: bool,
    ) -> RecordEntry:
        from installer.records import Hash
        from installer.records import RecordEntry
        from installer.utils import copyfileobj_with_hashing
        from installer.utils import make_file_executable

        target_path = Path(self.scheme_dict[scheme]) / path

        parent_folder = target_path.parent
        if not parent_folder.exists():
            # Due to the parallel installation it can happen
            # that two threads try to create the directory.
            parent_folder.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(delete=False) as fp:
            with open(fp.name, "wb") as f:
                hash_, size = copyfileobj_with_hashing(stream, f, self.hash_algorithm)
            if target_path.exists():
                # Contrary to the base library we don't raise an error here since it can
                # break pkgutil-style and pkg_resource-style namespace packages.
                # We instead log a warning and ignore it. See issue #9158.
                logger.warning(f"{target_path} already exists. Overwritting.")
            os.replace(fp.name, target_path)

        if is_executable:
            make_file_executable(target_path)

        return RecordEntry(path, Hash(self.hash_algorithm, hash_), size)


class WheelInstaller:
    def __init__(self, env: Env, wheel_destination_class=WheelDestination) -> None:
        self._env = env
        self.wheel_destination_class = wheel_destination_class

        script_kind: LauncherKind
        if not WINDOWS:
            script_kind = "posix"
        else:
            if platform.uname()[4].startswith("arm"):
                script_kind = "win-arm64" if sys.maxsize > 2**32 else "win-arm"
            else:
                script_kind = "win-amd64" if sys.maxsize > 2**32 else "win-ia32"
        self._script_kind = script_kind

        self._bytecode_optimization_levels: Collection[int] = ()
        self.invalid_wheels: dict[Path, list[str]] = {}

    def enable_bytecode_compilation(self, enable: bool = True) -> None:
        self._bytecode_optimization_levels = (-1,) if enable else ()

    def install(self, wheel: Path) -> None:
        with WheelFile.open(wheel) as source:
            try:
                # Content validation is temporarily disabled because of
                # pypa/installer's out of memory issues with big wheels. See
                # https://github.com/python-poetry/poetry/issues/7983
                source.validate_record(validate_contents=False)
            except _WheelFileValidationError as e:
                self.invalid_wheels[wheel] = e.issues

            scheme_dict = self._env.paths.copy()
            scheme_dict["headers"] = str(
                Path(scheme_dict["include"]) / source.distribution
            )
            destination = self.wheel_destination_class(
                scheme_dict,
                interpreter=str(self._env.python),
                script_kind=self._script_kind,
                bytecode_optimization_levels=self._bytecode_optimization_levels,
            )

            install(
                source=source,
                destination=destination,
                # Additional metadata that is generated by the installation tool.
                additional_metadata={
                    "INSTALLER": f"Poetry {__version__}".encode(),
                },
            )
