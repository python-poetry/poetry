from __future__ import annotations

import platform
import sys

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Collection
from typing import Iterable

from installer import install
from installer.destinations import SchemeDictionaryDestination
from installer.records import RecordEntry
from installer.records import parse_record_file
from installer.sources import WheelFile
from installer.sources import _WheelFileValidationError

from poetry.__version__ import __version__
from poetry.utils._compat import WINDOWS


if TYPE_CHECKING:
    from typing import BinaryIO

    from installer.scripts import LauncherKind
    from installer.utils import Scheme

    from poetry.utils.env import Env


class WheelDestination(SchemeDictionaryDestination):
    def __init__(
        self,
        source: WheelFile,
        scheme_dict: dict[str, str],
        interpreter: str,
        script_kind: LauncherKind,
        hash_algorithm: str = "sha256",
        bytecode_optimization_levels: Collection[int] = (),
        destdir: str | None = None,
    ) -> None:
        super().__init__(
            scheme_dict=scheme_dict,
            interpreter=interpreter,
            script_kind=script_kind,
            hash_algorithm=hash_algorithm,
            bytecode_optimization_levels=bytecode_optimization_levels,
            destdir=destdir,
        )
        self._source = source
        self.issues: list[str] = []

    def write_to_fs(
        self,
        scheme: Scheme,
        path: str,
        stream: BinaryIO,
        is_executable: bool,
    ) -> RecordEntry:
        from installer.records import Hash
        from installer.utils import copyfileobj_with_hashing
        from installer.utils import make_file_executable

        target_path = Path(self.scheme_dict[scheme]) / path
        if target_path.exists():
            # Contrary to the base library we don't raise an error
            # here since it can break namespace packages (like Poetry's)
            pass

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

    def for_source(self, source: WheelFile) -> WheelDestination:
        scheme_dict = self.scheme_dict.copy()

        scheme_dict["headers"] = str(Path(scheme_dict["headers"]) / source.distribution)

        return self.__class__(
            source=source,
            scheme_dict=scheme_dict,
            interpreter=self.interpreter,
            script_kind=self.script_kind,
            bytecode_optimization_levels=self.bytecode_optimization_levels,
        )

    def _validate_hash_and_size(
        self, records: Iterable[tuple[Scheme, RecordEntry]]
    ) -> None:
        record_lines = self._source.read_dist_info("RECORD").splitlines()
        record_mapping = {
            record[0]: record for record in parse_record_file(record_lines)
        }
        for item in self._source._zipfile.infolist():
            record_args = record_mapping.pop(item.filename, None)
            if not record_args:
                continue

            file_record = RecordEntry.from_elements(*record_args)
            computed_record = next(
                record for _, record in records if record.path == item.filename
            )
            if (
                file_record.hash_ is not None
                and computed_record.hash_ is not None
                and file_record.hash_ != computed_record.hash_
            ) or (
                file_record.size is not None
                and computed_record.size is not None
                and file_record.size != computed_record.size
            ):
                self.issues.append(
                    f"In {self._source._zipfile.filename}, hash / size of"
                    f" {item.filename} didn't match RECORD"
                )

    def finalize_installation(
        self,
        scheme: Scheme,
        record_file_path: str,
        records: Iterable[tuple[Scheme, RecordEntry]],
    ) -> None:
        self._validate_hash_and_size(records)
        return super().finalize_installation(scheme, record_file_path, records)


class WheelInstaller:
    def __init__(self, env: Env) -> None:
        self._env = env

        script_kind: LauncherKind
        if not WINDOWS:
            script_kind = "posix"
        else:
            if platform.uname()[4].startswith("arm"):
                script_kind = "win-arm64" if sys.maxsize > 2**32 else "win-arm"
            else:
                script_kind = "win-amd64" if sys.maxsize > 2**32 else "win-ia32"

        schemes = self._env.paths
        schemes["headers"] = schemes["include"]

        self._script_kind = script_kind
        self._schemes = schemes
        self._bytecode_compilation_enabled = False
        self.invalid_wheels: dict[Path, list[str]] = {}

    def enable_bytecode_compilation(self, enable: bool = True) -> None:
        self._bytecode_compilation_enabled = enable

    def install(self, wheel: Path) -> None:
        with WheelFile.open(wheel) as source:
            destination = WheelDestination(
                source=source,
                scheme_dict=self._schemes,
                interpreter=str(self._env.python),
                script_kind=self._script_kind,
            )
            destination.bytecode_optimization_levels = (
                (-1,) if self._bytecode_compilation_enabled else ()
            )
            destination = destination.for_source(source)
            try:
                # Content validation is disabled to avoid performing hash
                # computation on files twice. We perform this kind of validation
                # while installing the wheel. See _validate_hash_and_size.
                source.validate_record(validate_contents=False)
            except _WheelFileValidationError as e:
                self.invalid_wheels[wheel] = e.issues
            install(
                source=source,
                destination=destination,
                # Additional metadata that is generated by the installation tool.
                additional_metadata={
                    "INSTALLER": f"Poetry {__version__}".encode(),
                },
            )
            if destination.issues:
                self.invalid_wheels[wheel] = (
                    self.invalid_wheels.get(wheel, []) + destination.issues
                )
