from __future__ import unicode_literals

import os
import shutil

from collections import defaultdict

from poetry.semver.version import Version
from poetry.utils._compat import decode

from .builder import Builder
from .sdist import SdistBuilder


class EditableBuilder(Builder):
    def build(self):
        if self._package.build:
            # If the project has some kind of special
            # build needs we delegate to the setup.py file
            return self._setup_build()

        self._build_egg_info()
        self._build_egg_link()
        self._add_easy_install_entry()

    def _setup_build(self):
        builder = SdistBuilder(self._poetry, self._env, self._io)
        setup = self._path / "setup.py"
        has_setup = setup.exists()

        if has_setup:
            self._io.write_line(
                "<warning>A setup.py file already exists. Using it.</warning>"
            )
        else:
            with setup.open("w", encoding="utf-8") as f:
                f.write(decode(builder.build_setup()))

        try:
            if self._env.pip_version < Version(19, 0):
                self._env.run("python", "-m", "pip", "install", "-e", str(self._path))
            else:
                # Temporarily rename pyproject.toml
                shutil.move(
                    str(self._poetry.file), str(self._poetry.file.with_suffix(".tmp"))
                )
                try:
                    self._env.run(
                        "python", "-m", "pip", "install", "-e", str(self._path)
                    )
                finally:
                    shutil.move(
                        str(self._poetry.file.with_suffix(".tmp")),
                        str(self._poetry.file),
                    )
        finally:
            if not has_setup:
                os.remove(str(setup))

    def _build_egg_info(self):
        egg_info = self._path / "{}.egg-info".format(
            self._package.name.replace("-", "_")
        )
        egg_info.mkdir(exist_ok=True)

        with egg_info.joinpath("PKG-INFO").open("w", encoding="utf-8") as f:
            f.write(decode(self.get_metadata_content()))

        with egg_info.joinpath("entry_points.txt").open("w", encoding="utf-8") as f:
            entry_points = self.convert_entry_points()

            for group_name in sorted(entry_points):
                f.write("[{}]\n".format(group_name))
                for ep in sorted(entry_points[group_name]):
                    f.write(ep.replace(" ", "") + "\n")

                f.write("\n")

        with egg_info.joinpath("requires.txt").open("w", encoding="utf-8") as f:
            f.write(self._generate_requires())

    def _build_egg_link(self):
        egg_link = self._env.site_packages / "{}.egg-link".format(self._package.name)
        with egg_link.open("w", encoding="utf-8") as f:
            f.write(str(self._poetry.file.parent.resolve()) + "\n")
            f.write(".")

    def _add_easy_install_entry(self):
        easy_install_pth = self._env.site_packages / "easy-install.pth"
        path = str(self._poetry.file.parent.resolve())
        content = ""
        if easy_install_pth.exists():
            with easy_install_pth.open(encoding="utf-8") as f:
                content = f.read()

        if path in content:
            return

        content += "{}\n".format(path)

        with easy_install_pth.open("w", encoding="utf-8") as f:
            f.write(content)

    def _generate_requires(self):
        extras = defaultdict(list)

        requires = ""
        for dep in sorted(self._package.requires, key=lambda d: d.name):
            marker = dep.marker
            if marker.is_any():
                requires += "{}\n".format(dep.base_pep_508_name)
                continue

            extras[str(marker)].append(dep.base_pep_508_name)

        if extras:
            requires += "\n"

            for marker, deps in sorted(extras.items()):
                requires += "[:{}]\n".format(marker)

                for dep in deps:
                    requires += dep + "\n"

                requires += "\n"

        return requires
