from __future__ import annotations

import csv
import hashlib
import json
import os

from base64 import urlsafe_b64encode
from pathlib import Path
from typing import TYPE_CHECKING

from poetry.core.masonry.builders.builder import Builder
from poetry.core.masonry.builders.sdist import SdistBuilder
from poetry.core.masonry.utils.package_include import PackageInclude

from poetry.utils._compat import WINDOWS
from poetry.utils._compat import decode
from poetry.utils._compat import getencoding
from poetry.utils.env import build_environment
from poetry.utils.helpers import is_dir_writable
from poetry.utils.pip import pip_install


if TYPE_CHECKING:
    from cleo.io.io import IO

    from poetry.poetry import Poetry
    from poetry.utils.env import Env

SCRIPT_TEMPLATE = """\
#!{python}
import sys
from {module} import {callable_holder}

if __name__ == '__main__':
    sys.exit({callable_}())
"""

WINDOWS_CMD_TEMPLATE = """\
@echo off\r\n"{python}" "%~dp0\\{script}" %*\r\n
"""


class EditableBuilder(Builder):
    def __init__(self, poetry: Poetry, env: Env, io: IO) -> None:
        self._poetry: Poetry
        super().__init__(poetry)

        self._env = env
        self._io = io

    def build(self, target_dir: Path | None = None) -> Path:
        self._debug(
            f"  - Building package <c1>{self._package.name}</c1> in"
            " <info>editable</info> mode"
        )

        if self._package.build_script:
            if self._package.build_should_generate_setup():
                self._debug(
                    "  - <warning>Falling back on using a <b>setup.py</b></warning>"
                )
                self._setup_build()
                return self._path

            self._run_build_script(self._package.build_script)

        for removed in self._env.site_packages.remove_distribution_files(
            distribution_name=self._package.name
        ):
            self._debug(
                f"  - Removed <c2>{removed.name}</c2> directory from"
                f" <b>{removed.parent}</b>"
            )

        added_files = []
        added_files += self._add_pth()
        added_files += self._add_scripts()
        self._add_dist_info(added_files)

        return self._path

    def _run_build_script(self, build_script: str) -> None:
        with build_environment(poetry=self._poetry, env=self._env, io=self._io) as env:
            self._debug(f"  - Executing build script: <b>{build_script}</b>")
            env.run("python", str(self._path.joinpath(build_script)), call=True)

    def _setup_build(self) -> None:
        builder = SdistBuilder(self._poetry)
        setup = self._path / "setup.py"
        has_setup = setup.exists()

        if has_setup:
            self._io.write_error_line(
                "<warning>A setup.py file already exists. Using it.</warning>"
            )
        else:
            with setup.open("w", encoding="utf-8") as f:
                f.write(decode(builder.build_setup()))

        try:
            pip_install(self._path, self._env, upgrade=True, editable=True)
        finally:
            if not has_setup:
                os.remove(setup)

    def _add_pth(self) -> list[Path]:
        paths = {
            include.base.resolve().as_posix()
            for include in self._module.includes
            if isinstance(include, PackageInclude)
            and (include.is_module() or include.is_package())
        }

        content = "".join(decode(path + os.linesep) for path in paths)
        pth_file = Path(self._module.name).with_suffix(".pth")

        # remove any pre-existing pth files for this package
        for file in self._env.site_packages.find(path=pth_file, writable_only=True):
            self._debug(
                f"  - Removing existing <c2>{file.name}</c2> from <b>{file.parent}</b>"
                f" for {self._poetry.file.path.parent}"
            )
            file.unlink(missing_ok=True)

        try:
            pth_file = self._env.site_packages.write_text(
                pth_file, content, encoding=getencoding()
            )
            self._debug(
                f"  - Adding <c2>{pth_file.name}</c2> to <b>{pth_file.parent}</b> for"
                f" {self._poetry.file.path.parent}"
            )
            return [pth_file]
        except PermissionError:
            self._io.write_error_line(
                f"  - Failed to create <c2>{pth_file.name}</c2> for"
                f" {self._poetry.file.path.parent}"
            )
            return []

    def _add_scripts(self) -> list[Path]:
        added = []
        entry_points = self.convert_entry_points()

        for scripts_path in self._env.script_dirs:
            if is_dir_writable(path=scripts_path, create=True):
                break
        else:
            self._io.write_error_line(
                "  - Failed to find a suitable script installation directory for"
                f" {self._poetry.file.path.parent}"
            )
            return []

        scripts = entry_points.get("console_scripts", [])
        for script in scripts:
            name, script_with_extras = script.split(" = ")
            script_without_extras = script_with_extras.split("[")[0]
            try:
                module, callable_ = script_without_extras.split(":")
            except ValueError as exc:
                msg = (
                    f"Bad script ({name}): script needs to specify a function within a"
                    " module like: module(.submodule):function\nInstead got:"
                    f" {script_with_extras}"
                )
                if "not enough values" in str(exc):
                    msg += (
                        "\nHint: If the script depends on module-level code, try"
                        " wrapping it in a main() function and modifying your script"
                        f' like:\n{name} = "{script_with_extras}:main"'
                    )
                elif "too many values" in str(exc):
                    msg += '\nToo many ":" found!'

                raise ValueError(msg)

            callable_holder = callable_.split(".", 1)[0]

            script_file = scripts_path.joinpath(name)
            self._debug(
                f"  - Adding the <c2>{name}</c2> script to <b>{scripts_path}</b>"
            )
            with script_file.open("w", encoding="utf-8") as f:
                f.write(
                    decode(
                        SCRIPT_TEMPLATE.format(
                            python=self._env.python,
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
                cmd = WINDOWS_CMD_TEMPLATE.format(python=self._env.python, script=name)
                self._debug(
                    f"  - Adding the <c2>{cmd_script.name}</c2> script wrapper to"
                    f" <b>{scripts_path}</b>"
                )

                with cmd_script.open("w", encoding="utf-8") as f:
                    f.write(decode(cmd))

                added.append(cmd_script)

        return added

    def _add_dist_info(self, added_files: list[Path]) -> None:
        from poetry.core.masonry.builders.wheel import WheelBuilder

        builder = WheelBuilder(self._poetry)
        dist_info = self._env.site_packages.mkdir(Path(builder.dist_info))

        self._debug(
            f"  - Adding the <c2>{dist_info.name}</c2> directory to"
            f" <b>{dist_info.parent}</b>"
        )

        builder.prepare_metadata(dist_info.parent)
        for path in sorted(f for f in dist_info.rglob("*") if f.is_file()):
            added_files.append(path)

        with dist_info.joinpath("INSTALLER").open("w", encoding="utf-8") as f:
            f.write("poetry")

        added_files.append(dist_info.joinpath("INSTALLER"))

        # write PEP 610 metadata
        direct_url_json = dist_info.joinpath("direct_url.json")
        direct_url_json.write_text(
            json.dumps(
                {
                    "dir_info": {"editable": True},
                    "url": self._poetry.file.path.parent.absolute().as_uri(),
                }
            ),
            encoding="utf-8",
        )
        added_files.append(direct_url_json)

        record = dist_info.joinpath("RECORD")
        with record.open("w", encoding="utf-8", newline="") as f:
            csv_writer = csv.writer(f)
            for path in added_files:
                hash = self._get_file_hash(path)
                size = path.stat().st_size
                csv_writer.writerow((path, f"sha256={hash}", size))

            # RECORD itself is recorded with no hash or size
            csv_writer.writerow((record, "", ""))

    def _get_file_hash(self, filepath: Path) -> str:
        hashsum = hashlib.sha256()
        with filepath.open("rb") as src:
            while True:
                buf = src.read(1024 * 8)
                if not buf:
                    break
                hashsum.update(buf)

            src.seek(0)

        return urlsafe_b64encode(hashsum.digest()).decode("ascii").rstrip("=")

    def _debug(self, msg: str) -> None:
        if self._io.is_debug():
            self._io.write_line(msg)
