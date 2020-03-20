# -*- coding: utf-8 -*-
import os
import re
import tarfile
import time

from collections import defaultdict
from copy import copy
from gzip import GzipFile
from io import BytesIO
from posixpath import join as pjoin
from pprint import pformat

from poetry.utils._compat import Path
from poetry.utils._compat import encode
from poetry.utils._compat import to_str

from ..utils.helpers import normalize_file_permissions
from ..utils.package_include import PackageInclude
from .builder import Builder


SETUP = """\
# -*- coding: utf-8 -*-
from setuptools import setup

{before}
setup_kwargs = {{
    'name': {name!r},
    'version': {version!r},
    'description': {description!r},
    'long_description': {long_description!r},
    'author': {author!r},
    'author_email': {author_email!r},
    'maintainer': {maintainer!r},
    'maintainer_email': {maintainer_email!r},
    'url': {url!r},
    {extra}
}}
{after}

setup(**setup_kwargs)
"""


class SdistBuilder(Builder):

    format = "sdist"

    def build(self, target_dir=None):  # type: (Path) -> Path
        self._io.write_line(" - Building <info>sdist</info>")
        if target_dir is None:
            target_dir = self._path / "dist"

        if not target_dir.exists():
            target_dir.mkdir(parents=True)

        target = target_dir / "{}-{}.tar.gz".format(
            self._package.pretty_name, self._meta.version
        )
        gz = GzipFile(target.as_posix(), mode="wb")
        tar = tarfile.TarFile(
            target.as_posix(), mode="w", fileobj=gz, format=tarfile.PAX_FORMAT
        )

        try:
            tar_dir = "{}-{}".format(self._package.pretty_name, self._meta.version)

            files_to_add = self.find_files_to_add(exclude_build=False)

            for relpath in files_to_add:
                path = self._path / relpath
                tar_info = tar.gettarinfo(
                    str(path), arcname=pjoin(tar_dir, str(relpath))
                )
                tar_info = self.clean_tarinfo(tar_info)

                if tar_info.isreg():
                    with path.open("rb") as f:
                        tar.addfile(tar_info, f)
                else:
                    tar.addfile(tar_info)  # Symlinks & ?

            setup = self.build_setup()
            tar_info = tarfile.TarInfo(pjoin(tar_dir, "setup.py"))
            tar_info.size = len(setup)
            tar_info.mtime = time.time()
            tar.addfile(tar_info, BytesIO(setup))

            pkg_info = self.build_pkg_info()

            tar_info = tarfile.TarInfo(pjoin(tar_dir, "PKG-INFO"))
            tar_info.size = len(pkg_info)
            tar_info.mtime = time.time()
            tar.addfile(tar_info, BytesIO(pkg_info))
        finally:
            tar.close()
            gz.close()

        self._io.write_line(" - Built <comment>{}</comment>".format(target.name))

        return target

    def build_setup(self):  # type: () -> bytes
        before, extra, after = [], [], []
        package_dir = {}

        # If we have a build script, use it
        if self._package.build:
            after += [
                "from {} import *".format(self._package.build.split(".")[0]),
                "build(setup_kwargs)",
            ]

        modules = []
        packages = []
        package_data = {}
        for include in self._module.includes:
            if include.formats and "sdist" not in include.formats:
                continue

            if isinstance(include, PackageInclude):
                if include.is_package():
                    pkg_dir, _packages, _package_data = self.find_packages(include)

                    if pkg_dir is not None:
                        package_dir[""] = os.path.relpath(pkg_dir, str(self._path))

                    packages += [p for p in _packages if p not in packages]
                    package_data.update(_package_data)
                else:
                    module = include.elements[0].relative_to(include.base).stem

                    if include.source is not None:
                        package_dir[""] = str(include.base.relative_to(self._path))

                    if module not in modules:
                        modules.append(module)
            else:
                pass

        if package_dir:
            before.append("package_dir = \\\n{}\n".format(pformat(package_dir)))
            extra.append("'package_dir': package_dir,")

        if packages:
            before.append("packages = \\\n{}\n".format(pformat(sorted(packages))))
            extra.append("'packages': packages,")

        if package_data:
            before.append("package_data = \\\n{}\n".format(pformat(package_data)))
            extra.append("'package_data': package_data,")

        if modules:
            before.append("modules = \\\n{}".format(pformat(modules)))
            extra.append("'py_modules': modules,".format())

        dependencies, extras = self.convert_dependencies(
            self._package, self._package.requires
        )
        if dependencies:
            before.append(
                "install_requires = \\\n{}\n".format(pformat(sorted(dependencies)))
            )
            extra.append("'install_requires': install_requires,")

        if extras:
            before.append("extras_require = \\\n{}\n".format(pformat(extras)))
            extra.append("'extras_require': extras_require,")

        entry_points = self.convert_entry_points()
        if entry_points:
            before.append("entry_points = \\\n{}\n".format(pformat(entry_points)))
            extra.append("'entry_points': entry_points,")

        if self._package.python_versions != "*":
            python_requires = self._meta.requires_python

            extra.append("'python_requires': {!r},".format(python_requires))

        return encode(
            SETUP.format(
                before="\n".join(before),
                name=to_str(self._meta.name),
                version=to_str(self._meta.version),
                description=to_str(self._meta.summary),
                long_description=to_str(self._meta.description),
                author=to_str(self._meta.author),
                author_email=to_str(self._meta.author_email),
                maintainer=to_str(self._meta.maintainer),
                maintainer_email=to_str(self._meta.maintainer_email),
                url=to_str(self._meta.home_page),
                extra="\n    ".join(extra),
                after="\n".join(after),
            )
        )

    def build_pkg_info(self):
        return encode(self.get_metadata_content())

    def find_packages(self, include):
        """
        Discover subpackages and data.

        It also retrieves necessary files.
        """
        pkgdir = None
        if include.source is not None:
            pkgdir = str(include.base)

        base = str(include.elements[0].parent)

        pkg_name = include.package
        pkg_data = defaultdict(list)
        # Undocumented distutils feature:
        # the empty string matches all package names
        pkg_data[""].append("*")
        packages = [pkg_name]
        subpkg_paths = set()

        def find_nearest_pkg(rel_path):
            parts = rel_path.split(os.sep)
            for i in reversed(range(1, len(parts))):
                ancestor = "/".join(parts[:i])
                if ancestor in subpkg_paths:
                    pkg = ".".join([pkg_name] + parts[:i])
                    return pkg, "/".join(parts[i:])

            # Relative to the top-level package
            return pkg_name, Path(rel_path).as_posix()

        for path, dirnames, filenames in os.walk(str(base), topdown=True):
            if os.path.basename(path) == "__pycache__":
                continue

            from_top_level = os.path.relpath(path, base)
            if from_top_level == ".":
                continue

            is_subpkg = any(
                [filename.endswith(".py") for filename in filenames]
            ) and not all(
                [
                    self.is_excluded(Path(path, filename).relative_to(self._path))
                    for filename in filenames
                    if filename.endswith(".py")
                ]
            )
            if is_subpkg:
                subpkg_paths.add(from_top_level)
                parts = from_top_level.split(os.sep)
                packages.append(".".join([pkg_name] + parts))
            else:
                pkg, from_nearest_pkg = find_nearest_pkg(from_top_level)

                data_elements = [
                    f.relative_to(self._path)
                    for f in Path(path).glob("*")
                    if not f.is_dir()
                ]

                data = [e for e in data_elements if not self.is_excluded(e)]
                if not data:
                    continue

                if len(data) == len(data_elements):
                    pkg_data[pkg].append(pjoin(from_nearest_pkg, "*"))
                else:
                    for d in data:
                        if d.is_dir():
                            continue

                        pkg_data[pkg] += [pjoin(from_nearest_pkg, d.name) for d in data]

        # Sort values in pkg_data
        pkg_data = {k: sorted(v) for (k, v) in pkg_data.items() if v}

        return pkgdir, sorted(packages), pkg_data

    @classmethod
    def convert_dependencies(cls, package, dependencies):
        main = []
        extras = defaultdict(list)
        req_regex = re.compile(r"^(.+) \((.+)\)$")

        for dependency in dependencies:
            if dependency.is_optional():
                for extra_name, reqs in package.extras.items():
                    for req in reqs:
                        if req.name == dependency.name:
                            requirement = to_str(
                                dependency.to_pep_508(with_extras=False)
                            )
                            if ";" in requirement:
                                requirement, conditions = requirement.split(";")

                                requirement = requirement.strip()
                                if req_regex.match(requirement):
                                    requirement = req_regex.sub(
                                        "\\1\\2", requirement.strip()
                                    )

                                extras[extra_name + ":" + conditions.strip()].append(
                                    requirement
                                )

                                continue

                            requirement = requirement.strip()
                            if req_regex.match(requirement):
                                requirement = req_regex.sub(
                                    "\\1\\2", requirement.strip()
                                )
                            extras[extra_name].append(requirement)
                continue

            requirement = to_str(dependency.to_pep_508())
            if ";" in requirement:
                requirement, conditions = requirement.split(";")

                requirement = requirement.strip()
                if req_regex.match(requirement):
                    requirement = req_regex.sub("\\1\\2", requirement.strip())

                extras[":" + conditions.strip()].append(requirement)

                continue

            requirement = requirement.strip()
            if req_regex.match(requirement):
                requirement = req_regex.sub("\\1\\2", requirement.strip())

            main.append(requirement)

        return main, dict(extras)

    @classmethod
    def clean_tarinfo(cls, tar_info):
        """
        Clean metadata from a TarInfo object to make it more reproducible.

            - Set uid & gid to 0
            - Set uname and gname to ""
            - Normalise permissions to 644 or 755
            - Set mtime if not None
        """
        ti = copy(tar_info)
        ti.uid = 0
        ti.gid = 0
        ti.uname = ""
        ti.gname = ""
        ti.mode = normalize_file_permissions(ti.mode)

        return ti
