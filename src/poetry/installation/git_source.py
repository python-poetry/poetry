from __future__ import annotations

import contextlib
import hashlib
import json

from pathlib import Path
from typing import TYPE_CHECKING

from dulwich.errors import NotGitRepository
from requests.utils import atomic_open

from poetry.utils.helpers import remove_directory
from poetry.vcs.git import Git


if TYPE_CHECKING:
    from poetry.core.packages.package import Package


class EditableGitSource:
    """Manage the source trees referenced by installed editable Git wheels."""

    def __init__(self, environment: Path) -> None:
        self._environment = environment
        self._root = environment / "src" / ".poetry-git"

    def path_for(self, package: Package) -> Path:
        identity = json.dumps(
            [
                package.name,
                package.source_url,
                package.source_resolved_reference or package.source_reference,
                package.source_subdirectory,
            ]
        )
        digest = hashlib.sha256(identity.encode()).hexdigest()
        return self._root / f"{package.name}-{digest}"

    def _owns(self, path: Path, package: Package) -> bool:
        if path.parent != self._root or path.is_symlink():
            return False
        if not path.resolve().is_relative_to(self._environment.resolve()):
            return False
        marker = path.with_name(path.name + ".json")
        if marker.is_symlink():
            return False
        try:
            value = json.loads(marker.read_text(encoding="utf-8"))
            return isinstance(value, dict) and value.get("package") == package.name
        except (OSError, ValueError):
            return False

    def prepare(self, package: Package) -> Path:
        assert package.source_url is not None
        path = self.path_for(package)
        if not path.resolve().is_relative_to(self._environment.resolve()):
            raise RuntimeError(
                f"Editable Git checkout is outside the environment: {path}"
            )
        existed = path.exists()
        if existed and not self._owns(path, package):
            raise RuntimeError(f"Refusing to replace an unmanaged Git checkout: {path}")
        try:
            Git.clone(
                url=package.source_url,
                source_root=self._root,
                name=path.name,
                revision=package.source_resolved_reference or package.source_reference,
            )
            subdirectory = package.source_subdirectory
            if subdirectory:
                subdirectory = Path(subdirectory).as_posix()
                if subdirectory == ".":
                    subdirectory = None
            with atomic_open(path.with_name(path.name + ".json")) as marker:
                marker.write(
                    json.dumps(
                        {
                            "package": package.name,
                            "reference": package.source_reference,
                            "subdirectory": subdirectory,
                        }
                    ).encode("utf-8")
                )
        except Exception:
            if not existed:
                with contextlib.suppress(OSError):
                    if path.exists():
                        remove_directory(path, force=True)
                    path.with_name(path.name + ".json").unlink(missing_ok=True)
            raise
        return path

    def metadata(
        self, source: Path, package: Package
    ) -> tuple[str, str | None, str, str | None] | None:
        for path in (source, *source.parents):
            if not self._owns(path, package):
                continue
            try:
                info = Git.info(path)
                marker = json.loads(
                    path.with_name(path.name + ".json").read_text(encoding="utf-8")
                )
            except (OSError, ValueError, KeyError, NotGitRepository):
                return None
            subdirectory = source.relative_to(path).as_posix()
            return (
                info.origin,
                marker.get("reference"),
                info.revision,
                None if subdirectory == "." else subdirectory,
            )
        return None

    def remove(self, package: Package, *, preserve: Path | None = None) -> None:
        if not package.develop or not package.source_url:
            return
        source = Path(package.source_url)
        if source.is_absolute():
            for path in (source, *source.parents):
                if self._owns(path, package):
                    if not self._preserved(path, preserve):
                        self._delete(path)
                    return
        if package.source_type != "git":
            return

        # Local commits can change HEAD without changing the checkout directory.
        # Match the installed Git metadata instead of deriving its path from HEAD.
        matches = []
        candidates = dict.fromkeys(
            (self.path_for(package), *self._root.glob(f"{package.name}-*"))
        )
        for path in candidates:
            if not self._owns(path, package) or self._preserved(path, preserve):
                continue
            try:
                info = Git.info(path)
                marker = json.loads(
                    path.with_name(path.name + ".json").read_text(encoding="utf-8")
                )
            except (OSError, ValueError, KeyError, NotGitRepository):
                continue
            if (
                info.origin == package.source_url
                and info.revision == package.source_resolved_reference
                and marker.get("subdirectory") == package.source_subdirectory
            ):
                matches.append(path)
        if len(matches) == 1:
            self._delete(matches[0])

    @staticmethod
    def _preserved(path: Path, preserve: Path | None) -> bool:
        return preserve is not None and preserve.resolve().is_relative_to(
            path.resolve()
        )

    @staticmethod
    def _delete(path: Path) -> None:
        if path.exists():
            remove_directory(path, force=True)
        path.with_name(path.name + ".json").unlink()
