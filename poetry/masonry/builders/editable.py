from __future__ import unicode_literals

import hashlib
import os
import shutil

from base64 import urlsafe_b64encode

from poetry.core.masonry.builders.builder import Builder
from poetry.core.masonry.builders.sdist import SdistBuilder
from poetry.core.masonry.utils.package_include import PackageInclude
from poetry.core.semver.version import Version
from poetry.utils._compat import WINDOWS
from poetry.utils._compat import Path
from poetry.utils._compat import decode


SCRIPT_TEMPLATE = """\
#!{python}
from {module} import {callable_holder}

if __name__ == '__main__':
    {callable_}()
"""

WINDOWS_CMD_TEMPLATE = """\
@echo off\r\n"{python}" "%~dp0\\{script}" %*\r\n
"""


class EditableBuilder(Builder):
    def __init__(self, poetry, env, io):
        super(EditableBuilder, self).__init__(poetry)

        self._env = env
        self._io = io

    def build(self):
        self._debug(
            "  - Building package <c1>{}</c1> in <info>editable</info> mode".format(
                self._package.name
            )
        )

        if self._package.build_script:
            self._debug(
                "  - <warning>Falling back on using a <b>setup.py</b></warning>"
            )
            return self._setup_build()

        added_files = []
        added_files += self._add_pth()
        added_files += self._add_scripts()
        self._add_dist_info(added_files)

    def _setup_build(self):
        builder = SdistBuilder(self._poetry)
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
                self._env.run_pip("install", "-e", str(self._path), "--no-deps")
            else:
                # Temporarily rename pyproject.toml
                shutil.move(
                    str(self._poetry.file), str(self._poetry.file.with_suffix(".tmp"))
                )
                try:
                    self._env.run_pip("install", "-e", str(self._path), "--no-deps")
                finally:
                    shutil.move(
                        str(self._poetry.file.with_suffix(".tmp")),
                        str(self._poetry.file),
                    )
        finally:
            if not has_setup:
                os.remove(str(setup))

    def _add_pth(self):
        pth = self._env.site_packages.joinpath(self._module.name).with_suffix(".pth")
        self._debug(
            "  - Adding <c2>{}</c2> to <b>{}</b> for {}".format(
                pth.name, self._env.site_packages, self._poetry.file.parent
            )
        )

        paths = set()
        for include in self._module.includes:
            if isinstance(include, PackageInclude) and (
                include.is_module() or include.is_package()
            ):
                paths.add(include.base.resolve().as_posix())

        with pth.open("w", encoding="utf-8") as f:
            for path in paths:
                f.write(decode(path + os.linesep))

        return [pth]

    def _add_scripts(self):
        added = []
        entry_points = self.convert_entry_points()
        scripts_path = Path(self._env.paths["scripts"])

        scripts = entry_points.get("console_scripts", [])
        for script in scripts:
            name, script = script.split(" = ")
            module, callable_ = script.split(":")
            callable_holder = callable_.rsplit(".", 1)[0]

            script_file = scripts_path.joinpath(name)
            self._debug(
                "  - Adding the <c2>{}</c2> script to <b>{}</b>".format(
                    name, scripts_path
                )
            )
            with script_file.open("w", encoding="utf-8") as f:
                f.write(
                    decode(
                        SCRIPT_TEMPLATE.format(
                            python=self._env._bin("python"),
                            module=module,
                            callable_holder=callable_holder,
                            callable_=callable_,
                        )
                    )
                )

            script_file.chmod(0o755)

            added.append(script_file)

            if WINDOWS:
                cmd_script = script_file.with_suffix(".cmd")
                cmd = WINDOWS_CMD_TEMPLATE.format(
                    python=self._env._bin("python"), script=name
                )
                self._debug(
                    "  - Adding the <c2>{}</c2> script wrapper to <b>{}</b>".format(
                        cmd_script.name, scripts_path
                    )
                )

                with cmd_script.open("w", encoding="utf-8") as f:
                    f.write(decode(cmd))

                added.append(cmd_script)

        return added

    def _add_dist_info(self, added_files):
        from poetry.core.masonry.builders.wheel import WheelBuilder

        added_files = added_files[:]

        builder = WheelBuilder(self._poetry)
        dist_info = self._env.site_packages.joinpath(builder.dist_info)

        self._debug(
            "  - Adding the <c2>{}</c2> directory to <b>{}</b>".format(
                dist_info.name, self._env.site_packages
            )
        )

        if dist_info.exists():
            shutil.rmtree(str(dist_info))

        dist_info.mkdir()

        with dist_info.joinpath("METADATA").open("w", encoding="utf-8") as f:
            builder._write_metadata_file(f)

        added_files.append(dist_info.joinpath("METADATA"))

        with dist_info.joinpath("INSTALLER").open("w", encoding="utf-8") as f:
            f.write("poetry")

        added_files.append(dist_info.joinpath("INSTALLER"))

        if self.convert_entry_points():
            with dist_info.joinpath("entry_points.txt").open(
                "w", encoding="utf-8"
            ) as f:
                builder._write_entry_points(f)

            added_files.append(dist_info.joinpath("entry_points.txt"))

        with dist_info.joinpath("RECORD").open("w", encoding="utf-8") as f:
            for path in added_files:
                hash = self._get_file_hash(path)
                size = path.stat().st_size
                f.write("{},sha256={},{}\n".format(str(path), hash, size))

            # RECORD itself is recorded with no hash or size
            f.write("{},,\n".format(dist_info.joinpath("RECORD")))

    def _get_file_hash(self, filepath):
        hashsum = hashlib.sha256()
        with filepath.open("rb") as src:
            while True:
                buf = src.read(1024 * 8)
                if not buf:
                    break
                hashsum.update(buf)

            src.seek(0)

        return urlsafe_b64encode(hashsum.digest()).decode("ascii").rstrip("=")

    def _debug(self, msg):
        if self._io.is_debug():
            self._io.write_line(msg)
