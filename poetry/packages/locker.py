import json

import poetry.packages
import poetry.repositories

from hashlib import sha256
from tomlkit import document
from typing import List

from poetry.utils._compat import Path
from poetry.utils.toml_file import TomlFile
from poetry.version.markers import parse_marker


class Locker:

    _relevant_keys = ["dependencies", "dev-dependencies", "source", "extras"]

    def __init__(self, lock, local_config):  # type: (Path, dict) -> None
        self._lock = TomlFile(lock)
        self._local_config = local_config
        self._lock_data = None
        self._content_hash = self._get_content_hash()

    @property
    def lock(self):  # type: () -> TomlFile
        return self._lock

    @property
    def lock_data(self):
        if self._lock_data is None:
            self._lock_data = self._get_lock_data()

        return self._lock_data

    def is_locked(self):  # type: () -> bool
        """
        Checks whether the locker has been locked (lockfile found).
        """
        if not self._lock.exists():
            return False

        return "package" in self.lock_data

    def is_fresh(self):  # type: () -> bool
        """
        Checks whether the lock file is still up to date with the current hash.
        """
        lock = self._lock.read()
        metadata = lock.get("metadata", {})

        if "content-hash" in metadata:
            return self._content_hash == lock["metadata"]["content-hash"]

        return False

    def locked_repository(
        self, with_dev_reqs=False
    ):  # type: (bool) -> poetry.repositories.Repository
        """
        Searches and returns a repository of locked packages.
        """
        if not self.is_locked():
            return poetry.repositories.Repository()

        lock_data = self.lock_data
        packages = poetry.repositories.Repository()

        if with_dev_reqs:
            locked_packages = lock_data["package"]
        else:
            locked_packages = [
                p for p in lock_data["package"] if p["category"] == "main"
            ]

        if not locked_packages:
            return packages

        for info in locked_packages:
            package = poetry.packages.Package(
                info["name"], info["version"], info["version"]
            )
            package.description = info.get("description", "")
            package.category = info["category"]
            package.optional = info["optional"]
            package.hashes = lock_data["metadata"]["hashes"][info["name"]]
            package.python_versions = info["python-versions"]

            if "marker" in info:
                package.marker = parse_marker(info["marker"])
            else:
                # Compatibility for old locks
                if "requirements" in info:
                    dep = poetry.packages.Dependency("foo", "0.0.0")
                    for name, value in info["requirements"].items():
                        if name == "python":
                            dep.python_versions = value
                        elif name == "platform":
                            dep.platform = value

                    split_dep = dep.to_pep_508(False).split(";")
                    if len(split_dep) > 1:
                        package.marker = parse_marker(split_dep[1].strip())

            for dep_name, constraint in info.get("dependencies", {}).items():
                if isinstance(constraint, list):
                    for c in constraint:
                        package.add_dependency(dep_name, c)

                    continue

                package.add_dependency(dep_name, constraint)

            if "source" in info:
                package.source_type = info["source"]["type"]
                package.source_url = info["source"]["url"]
                package.source_reference = info["source"]["reference"]

            packages.add_package(package)

        return packages

    def set_lock_data(self, root, packages):  # type: () -> bool
        hashes = {}
        packages = self._lock_packages(packages)
        # Retrieving hashes
        for package in packages:
            if package["name"] not in hashes:
                hashes[package["name"]] = []

            hashes[package["name"]] += package["hashes"]
            del package["hashes"]

        lock = document()
        lock["package"] = packages

        if root.extras:
            lock["extras"] = {
                extra: [dep.pretty_name for dep in deps]
                for extra, deps in root.extras.items()
            }

        lock["metadata"] = {
            "python-versions": root.python_versions,
            "content-hash": self._content_hash,
            "hashes": hashes,
        }

        if not self.is_locked() or lock != self.lock_data:
            self._write_lock_data(lock)

            return True

        return False

    def _write_lock_data(self, data):
        self.lock.write(data)

        # Checking lock file data consistency
        if data != self.lock.read():
            raise RuntimeError("Inconsistent lock file data.")

        self._lock_data = None

    def _get_content_hash(self):  # type: () -> str
        """
        Returns the sha256 hash of the sorted content of the pyproject file.
        """
        content = self._local_config

        relevant_content = {}
        for key in self._relevant_keys:
            relevant_content[key] = content.get(key)

        content_hash = sha256(
            json.dumps(relevant_content, sort_keys=True).encode()
        ).hexdigest()

        return content_hash

    def _get_lock_data(self):  # type: () -> dict
        if not self._lock.exists():
            raise RuntimeError("No lockfile found. Unable to read locked packages")

        return self._lock.read()

    def _lock_packages(
        self, packages
    ):  # type: (List['poetry.packages.Package']) -> list
        locked = []

        for package in sorted(packages, key=lambda x: x.name):
            spec = self._dump_package(package)

            locked.append(spec)

        return locked

    def _dump_package(self, package):  # type: (poetry.packages.Package) -> dict
        dependencies = {}
        for dependency in sorted(package.requires, key=lambda d: d.name):
            if dependency.is_optional() and not dependency.is_activated():
                continue

            if dependency.pretty_name not in dependencies:
                dependencies[dependency.pretty_name] = []

            constraint = {"version": str(dependency.pretty_constraint)}

            if not dependency.python_constraint.is_any():
                constraint["python"] = str(dependency.python_constraint)

            if len(constraint) == 1:
                dependencies[dependency.pretty_name].append(constraint["version"])
            else:
                dependencies[dependency.pretty_name].append(constraint)

        data = {
            "name": package.pretty_name,
            "version": package.pretty_version,
            "description": package.description or "",
            "category": package.category,
            "optional": package.optional,
            "python-versions": package.python_versions,
            "hashes": sorted(package.hashes),
        }
        if not package.marker.is_any():
            data["marker"] = str(package.marker)

        if dependencies:
            for k, constraints in dependencies.items():
                if len(constraints) == 1:
                    dependencies[k] = constraints[0]

            data["dependencies"] = dependencies

        if package.source_type:
            data["source"] = {
                "type": package.source_type,
                "url": package.source_url,
                "reference": package.source_reference,
            }

        return data
