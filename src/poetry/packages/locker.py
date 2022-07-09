from __future__ import annotations

import json
import logging
import os
import re

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from poetry.core.packages.dependency import Dependency
from poetry.core.packages.package import Package
from poetry.core.semver.helpers import parse_constraint
from poetry.core.semver.version import Version
from poetry.core.toml.file import TOMLFile
from poetry.core.version.markers import parse_marker
from poetry.core.version.requirements import InvalidRequirement
from tomlkit import array
from tomlkit import document
from tomlkit import inline_table
from tomlkit import item
from tomlkit import table
from tomlkit.exceptions import TOMLKitError
from tomlkit.items import Array

from poetry.packages import DependencyPackage
from poetry.utils.extras import get_extra_package_names


if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Iterator
    from collections.abc import Sequence

    from poetry.core.packages.directory_dependency import DirectoryDependency
    from poetry.core.packages.file_dependency import FileDependency
    from poetry.core.packages.url_dependency import URLDependency
    from poetry.core.packages.vcs_dependency import VCSDependency
    from poetry.core.version.markers import BaseMarker
    from tomlkit.items import Table
    from tomlkit.toml_document import TOMLDocument

    from poetry.repositories import Repository

logger = logging.getLogger(__name__)


class Locker:
    _VERSION = "1.1"

    _legacy_keys = ["dependencies", "source", "extras", "dev-dependencies"]
    _relevant_keys = [*_legacy_keys, "group"]

    def __init__(self, lock: str | Path, local_config: dict[str, Any]) -> None:
        self._lock = TOMLFile(lock)
        self._local_config = local_config
        self._lock_data: TOMLDocument | None = None
        self._content_hash = self._get_content_hash()

    @property
    def lock(self) -> TOMLFile:
        return self._lock

    @property
    def lock_data(self) -> TOMLDocument:
        if self._lock_data is None:
            self._lock_data = self._get_lock_data()

        return self._lock_data

    def is_locked(self) -> bool:
        """
        Checks whether the locker has been locked (lockfile found).
        """
        if not self._lock.exists():
            return False

        return "package" in self.lock_data

    def is_fresh(self) -> bool:
        """
        Checks whether the lock file is still up to date with the current hash.
        """
        lock = self._lock.read()
        metadata = lock.get("metadata", {})

        if "content-hash" in metadata:
            fresh: bool = self._content_hash == metadata["content-hash"]
            return fresh

        return False

    def locked_repository(self) -> Repository:
        """
        Searches and returns a repository of locked packages.
        """
        from poetry.factory import Factory
        from poetry.repositories import Repository

        if not self.is_locked():
            return Repository()

        lock_data = self.lock_data
        packages = Repository()
        locked_packages = cast("list[dict[str, Any]]", lock_data["package"])

        if not locked_packages:
            return packages

        for info in locked_packages:
            source = info.get("source", {})
            source_type = source.get("type")
            url = source.get("url")
            if source_type in ["directory", "file"]:
                url = self._lock.path.parent.joinpath(url).resolve().as_posix()

            package = Package(
                info["name"],
                info["version"],
                info["version"],
                source_type=source_type,
                source_url=url,
                source_reference=source.get("reference"),
                source_resolved_reference=source.get("resolved_reference"),
            )
            package.description = info.get("description", "")
            package.category = info.get("category", "main")
            package.optional = info["optional"]
            metadata = cast("dict[str, Any]", lock_data["metadata"])
            name = info["name"]
            if "hashes" in metadata:
                # Old lock so we create dummy files from the hashes
                hashes = cast("dict[str, Any]", metadata["hashes"])
                package.files = [{"name": h, "hash": h} for h in hashes[name]]
            else:
                files = metadata["files"][name]
                package.files = files

            package.python_versions = info["python-versions"]
            extras = info.get("extras", {})
            if extras:
                for name, deps in extras.items():
                    package.extras[name] = []

                    for dep in deps:
                        try:
                            dependency = Dependency.create_from_pep_508(dep)
                        except InvalidRequirement:
                            # handle lock files with invalid PEP 508
                            m = re.match(r"^(.+?)(?:\[(.+?)])?(?:\s+\((.+)\))?$", dep)
                            if not m:
                                raise
                            dep_name = m.group(1)
                            extras = m.group(2) or ""
                            constraint = m.group(3) or "*"
                            dependency = Dependency(
                                dep_name, constraint, extras=extras.split(",")
                            )
                        package.extras[name].append(dependency)

            if "marker" in info:
                package.marker = parse_marker(info["marker"])
            else:
                # Compatibility for old locks
                if "requirements" in info:
                    dep = Dependency("foo", "0.0.0")
                    for name, value in info["requirements"].items():
                        if name == "python":
                            dep.python_versions = value
                        elif name == "platform":
                            dep.platform = value

                    split_dep = dep.to_pep_508(False).split(";")
                    if len(split_dep) > 1:
                        package.marker = parse_marker(split_dep[1].strip())

            for dep_name, constraint in info.get("dependencies", {}).items():
                root_dir = self._lock.path.parent
                if package.source_type == "directory":
                    # root dir should be the source of the package relative to the lock
                    # path
                    assert package.source_url is not None
                    root_dir = Path(package.source_url)

                if isinstance(constraint, list):
                    for c in constraint:
                        package.add_dependency(
                            Factory.create_dependency(dep_name, c, root_dir=root_dir)
                        )

                    continue

                package.add_dependency(
                    Factory.create_dependency(dep_name, constraint, root_dir=root_dir)
                )

            if "develop" in info:
                package.develop = info["develop"]

            packages.add_package(package)

        return packages

    @staticmethod
    def __get_locked_package(
        dependency: Dependency,
        packages_by_name: dict[str, list[Package]],
        decided: dict[Package, Dependency] | None = None,
    ) -> Package | None:
        """
        Internal helper to identify corresponding locked package using dependency
        version constraints.
        """
        decided = decided or {}

        # Get the packages that are consistent with this dependency.
        packages = [
            package
            for package in packages_by_name.get(dependency.name, [])
            if package.python_constraint.allows_all(dependency.python_constraint)
            and dependency.constraint.allows(package.version)
        ]

        # If we've previously made a choice that is compatible with the current
        # requirement, stick with it.
        for package in packages:
            old_decision = decided.get(package)
            if (
                old_decision is not None
                and not old_decision.marker.intersect(dependency.marker).is_empty()
            ):
                return package

        return next(iter(packages), None)

    @classmethod
    def __walk_dependencies(
        cls,
        dependencies: list[Dependency],
        packages_by_name: dict[str, list[Package]],
    ) -> dict[Package, Dependency]:
        nested_dependencies: dict[Package, Dependency] = {}

        visited: set[tuple[Dependency, BaseMarker]] = set()
        while dependencies:
            requirement = dependencies.pop(0)
            if (requirement, requirement.marker) in visited:
                continue
            visited.add((requirement, requirement.marker))

            locked_package = cls.__get_locked_package(
                requirement, packages_by_name, nested_dependencies
            )

            if not locked_package:
                raise RuntimeError(f"Dependency walk failed at {requirement}")

            if requirement.extras:
                locked_package = locked_package.with_features(requirement.extras)

            # create dependency from locked package to retain dependency metadata
            # if this is not done, we can end-up with incorrect nested dependencies
            constraint = requirement.constraint
            marker = requirement.marker
            requirement = locked_package.to_dependency()
            requirement.marker = requirement.marker.intersect(marker)

            requirement.set_constraint(constraint)

            for require in locked_package.requires:
                if require.in_extras and locked_package.features.isdisjoint(
                    require.in_extras
                ):
                    continue

                require = deepcopy(require)
                require.marker = require.marker.intersect(
                    requirement.marker.without_extras()
                )
                if not require.marker.is_empty():
                    dependencies.append(require)

            key = locked_package
            if key not in nested_dependencies:
                nested_dependencies[key] = requirement
            else:
                nested_dependencies[key].marker = nested_dependencies[key].marker.union(
                    requirement.marker
                )

        return nested_dependencies

    @classmethod
    def get_project_dependencies(
        cls,
        project_requires: list[Dependency],
        locked_packages: list[Package],
    ) -> Iterable[tuple[Package, Dependency]]:
        # group packages entries by name, this is required because requirement might use
        # different constraints.
        packages_by_name: dict[str, list[Package]] = {}
        for pkg in locked_packages:
            if pkg.name not in packages_by_name:
                packages_by_name[pkg.name] = []
            packages_by_name[pkg.name].append(pkg)

        # Put higher versions first so that we prefer them.
        for packages in packages_by_name.values():
            packages.sort(
                key=lambda package: package.version,
                reverse=True,
            )

        nested_dependencies = cls.__walk_dependencies(
            dependencies=project_requires,
            packages_by_name=packages_by_name,
        )

        return nested_dependencies.items()

    def get_project_dependency_packages(
        self,
        project_requires: list[Dependency],
        project_python_marker: BaseMarker | None = None,
        extras: bool | Sequence[str] | None = None,
    ) -> Iterator[DependencyPackage]:
        # Apply the project python marker to all requirements.
        if project_python_marker is not None:
            marked_requires: list[Dependency] = []
            for require in project_requires:
                require = deepcopy(require)
                require.marker = require.marker.intersect(project_python_marker)
                marked_requires.append(require)
            project_requires = marked_requires

        repository = self.locked_repository()

        # Build a set of all packages required by our selected extras
        extra_package_names: set[str] | None = None

        if extras is not True:
            extra_package_names = set(
                get_extra_package_names(
                    repository.packages,
                    self.lock_data.get("extras", {}),
                    extras or (),
                )
            )

        # If a package is optional and we haven't opted in to it, do not select
        selected = []
        for dependency in project_requires:
            try:
                package = repository.find_packages(dependency=dependency)[0]
            except IndexError:
                continue

            if extra_package_names is not None and (
                package.optional and package.name not in extra_package_names
            ):
                # a package is locked as optional, but is not activated via extras
                continue

            selected.append(dependency)

        for package, dependency in self.get_project_dependencies(
            project_requires=selected,
            locked_packages=repository.packages,
        ):
            yield DependencyPackage(dependency=dependency, package=package)

    def set_lock_data(self, root: Package, packages: list[Package]) -> bool:
        files: dict[str, Any] = table()
        package_specs = self._lock_packages(packages)
        # Retrieving hashes
        for package in package_specs:
            if package["name"] not in files:
                files[package["name"]] = []

            for f in package["files"]:
                file_metadata = inline_table()
                for k, v in sorted(f.items()):
                    file_metadata[k] = v

                files[package["name"]].append(file_metadata)

            if files[package["name"]]:
                package_files = item(files[package["name"]])
                assert isinstance(package_files, Array)
                files[package["name"]] = package_files.multiline(True)

            del package["files"]

        lock = document()
        lock["package"] = package_specs

        if root.extras:
            lock["extras"] = {
                extra: [dep.pretty_name for dep in deps]
                for extra, deps in sorted(root.extras.items())
            }

        lock["metadata"] = {
            "lock-version": self._VERSION,
            "python-versions": root.python_versions,
            "content-hash": self._content_hash,
            "files": files,
        }

        if not self.is_locked() or lock != self.lock_data:
            self._write_lock_data(lock)

            return True

        return False

    def _write_lock_data(self, data: TOMLDocument) -> None:
        self.lock.write(data)

        # Checking lock file data consistency
        if data != self.lock.read():
            raise RuntimeError("Inconsistent lock file data.")

        self._lock_data = None

    def _get_content_hash(self) -> str:
        """
        Returns the sha256 hash of the sorted content of the pyproject file.
        """
        content = self._local_config

        relevant_content = {}
        for key in self._relevant_keys:
            data = content.get(key)

            if data is None and key not in self._legacy_keys:
                continue

            relevant_content[key] = data

        return sha256(json.dumps(relevant_content, sort_keys=True).encode()).hexdigest()

    def _get_lock_data(self) -> TOMLDocument:
        if not self._lock.exists():
            raise RuntimeError("No lockfile found. Unable to read locked packages")

        try:
            lock_data: TOMLDocument = self._lock.read()
        except TOMLKitError as e:
            raise RuntimeError(f"Unable to read the lock file ({e}).")

        metadata = cast("Table", lock_data["metadata"])
        lock_version = Version.parse(metadata.get("lock-version", "1.0"))
        current_version = Version.parse(self._VERSION)
        # We expect the locker to be able to read lock files
        # from the same semantic versioning range
        accepted_versions = parse_constraint(
            f"^{Version.from_parts(current_version.major, 0)}"
        )
        lock_version_allowed = accepted_versions.allows(lock_version)
        if lock_version_allowed and current_version < lock_version:
            logger.warning(
                "The lock file might not be compatible with the current version of"
                " Poetry.\nUpgrade Poetry to ensure the lock file is read properly or,"
                " alternatively, regenerate the lock file with the `poetry lock`"
                " command."
            )
        elif not lock_version_allowed:
            raise RuntimeError(
                "The lock file is not compatible with the current version of Poetry.\n"
                "Upgrade Poetry to be able to read the lock file or, alternatively, "
                "regenerate the lock file with the `poetry lock` command."
            )

        return lock_data

    def _lock_packages(self, packages: list[Package]) -> list[dict[str, Any]]:
        locked = []

        for package in sorted(
            packages,
            key=lambda x: (
                x.name,
                x.version,
                x.source_type or "",
                x.source_url or "",
                x.source_subdirectory or "",
                x.source_reference or "",
                x.source_resolved_reference or "",
            ),
        ):
            spec = self._dump_package(package)

            locked.append(spec)

        return locked

    def _dump_package(self, package: Package) -> dict[str, Any]:
        dependencies: dict[str, list[Any]] = {}
        for dependency in sorted(
            package.requires,
            key=lambda d: d.name,
        ):
            if dependency.pretty_name not in dependencies:
                dependencies[dependency.pretty_name] = []

            constraint = inline_table()

            if dependency.is_directory():
                dependency = cast("DirectoryDependency", dependency)
                constraint["path"] = dependency.path.as_posix()

                if dependency.develop:
                    constraint["develop"] = True

            elif dependency.is_file():
                dependency = cast("FileDependency", dependency)
                constraint["path"] = dependency.path.as_posix()

            elif dependency.is_url():
                dependency = cast("URLDependency", dependency)
                constraint["url"] = dependency.url

            elif dependency.is_vcs():
                dependency = cast("VCSDependency", dependency)
                constraint[dependency.vcs] = dependency.source

                if dependency.branch:
                    constraint["branch"] = dependency.branch
                elif dependency.tag:
                    constraint["tag"] = dependency.tag
                elif dependency.rev:
                    constraint["rev"] = dependency.rev
            else:
                constraint["version"] = str(dependency.pretty_constraint)

            if dependency.extras:
                constraint["extras"] = sorted(dependency.extras)

            if dependency.is_optional():
                constraint["optional"] = True

            if not dependency.marker.is_any():
                constraint["markers"] = str(dependency.marker)

            dependencies[dependency.pretty_name].append(constraint)

        # All the constraints should have the same type,
        # but we want to simplify them if it's possible
        for dependency_name, constraints in dependencies.items():
            if all(
                len(constraint) == 1 and "version" in constraint
                for constraint in constraints
            ):
                dependencies[dependency_name] = [
                    constraint["version"] for constraint in constraints
                ]

        data: dict[str, Any] = {
            "name": package.pretty_name,
            "version": package.pretty_version,
            "description": package.description or "",
            "category": package.category,
            "optional": package.optional,
            "python-versions": package.python_versions,
            "files": sorted(
                package.files,
                key=lambda x: x["file"],  # type: ignore[no-any-return]
            ),
        }

        if dependencies:
            data["dependencies"] = table()
            for k, constraints in dependencies.items():
                if len(constraints) == 1:
                    data["dependencies"][k] = constraints[0]
                else:
                    data["dependencies"][k] = array().multiline(True)
                    for constraint in constraints:
                        data["dependencies"][k].append(constraint)

        if package.extras:
            extras = {}
            for name, deps in package.extras.items():
                # TODO: This should use dep.to_pep_508() once this is fixed
                # https://github.com/python-poetry/poetry-core/pull/102
                extras[name] = [
                    dep.base_pep_508_name if not dep.constraint.is_any() else dep.name
                    for dep in deps
                ]

            data["extras"] = extras

        if package.source_url:
            url = package.source_url
            if package.source_type in ["file", "directory"]:
                # The lock file should only store paths relative to the root project
                url = Path(
                    os.path.relpath(
                        Path(url).as_posix(), self._lock.path.parent.as_posix()
                    )
                ).as_posix()

            data["source"] = {}

            if package.source_type:
                data["source"]["type"] = package.source_type

            data["source"]["url"] = url

            if package.source_reference:
                data["source"]["reference"] = package.source_reference

            if package.source_resolved_reference:
                data["source"]["resolved_reference"] = package.source_resolved_reference

            if package.source_type in ["directory", "git"]:
                data["develop"] = package.develop

        return data


class NullLocker(Locker):
    def set_lock_data(self, root: Package, packages: list[Package]) -> bool:
        pass
