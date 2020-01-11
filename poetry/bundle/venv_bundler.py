import sys

from typing import TYPE_CHECKING
from typing import Optional
from typing import cast

from .bundler import Bundler


if TYPE_CHECKING:
    from pathlib import Path
    from typing import Optional

    from cleo.io.io import IO
    from cleo.io.outputs.section_output import SectionOutput  # noqa

    from poetry.poetry import Poetry


class VenvBundler(Bundler):
    @property
    def name(self):  # type: () -> str
        return "venv"

    def bundle(
        self,
        poetry: "Poetry",
        io: "IO",
        path: "Path",
        executable: Optional[str] = None,
        remove: bool = False,
    ) -> bool:
        from pathlib import Path

        from cleo.io.null_io import NullIO

        from poetry.core.masonry.builders.wheel import WheelBuilder
        from poetry.core.masonry.utils.module import ModuleOrPackageNotFound
        from poetry.core.packages.package import Package
        from poetry.core.semver.version import Version
        from poetry.installation.installer import Installer
        from poetry.installation.operations.install import Install
        from poetry.utils.env import EnvManager
        from poetry.utils.env import SystemEnv
        from poetry.utils.env import VirtualEnv
        from poetry.utils.helpers import temporary_directory

        warnings = []

        manager = EnvManager(poetry)
        if executable is not None:
            executable, python_version = manager.get_executable_info(executable)
        else:
            version_info = SystemEnv(Path(sys.prefix)).get_version_info()
            python_version = Version(*version_info[:3])

        message = self._get_message(poetry, path)
        if io.is_decorated() and not io.is_debug():
            io = io.section()

        io.write_line(message)

        if path.exists():
            env = VirtualEnv(path)
            env_python_version = Version(*env.version_info[:3])
            if not env.is_sane() or env_python_version != python_version or remove:
                self._write(
                    io, message + ": <info>Removing existing virtual environment</info>"
                )

                manager.remove_venv(str(path))

                self._write(
                    io,
                    message
                    + ": <info>Creating a virtual environment using Python <b>{}</b></info>".format(
                        python_version
                    ),
                )

                manager.build_venv(str(path), executable=executable)
            else:
                self._write(
                    io,
                    message
                    + ": <info>Using existing virtual environment</info>".format(
                        python_version
                    ),
                )
        else:
            self._write(
                io,
                message
                + ": <info>Creating a virtual environment using Python <b>{}</b></info>".format(
                    python_version
                ),
            )

            manager.build_venv(str(path), executable=executable)

        env = VirtualEnv(path)

        self._write(
            io,
            message + ": <info>Installing dependencies</info>".format(python_version),
        )

        installer = Installer(
            NullIO() if not io.is_debug() else io,
            env,
            poetry.package,
            poetry.locker,
            poetry.pool,
            poetry.config,
        )
        installer.remove_untracked()
        installer.use_executor(poetry.config.get("experimental.new-installer", False))

        return_code = installer.run()
        if return_code:
            self._write(
                io,
                self._get_message(poetry, path, error=True)
                + ": <error>Failed</> at step <b>Installing dependencies</b>".format(
                    python_version
                ),
            )
            return False

        self._write(
            io,
            message
            + ": <info>Installing <c1>{}</c1> (<b>{}</b>)</info>".format(
                poetry.package.pretty_name, poetry.package.pretty_version
            ),
        )

        # Build a wheel of the project in a temporary directory
        # and install it in the newly create virtual environment
        with temporary_directory() as directory:
            try:
                wheel_name = WheelBuilder.make_in(poetry, directory=Path(directory))
                wheel = Path(directory).joinpath(wheel_name)
                package = Package(
                    poetry.package.name,
                    poetry.package.version,
                    source_type="file",
                    source_url=wheel,
                )
                installer.executor.execute([Install(package)])
            except ModuleOrPackageNotFound:
                warnings.append(
                    "The root package was not installed because no matching module or package was found."
                )

        self._write(io, self._get_message(poetry, path, done=True))

        if warnings:
            for warning in warnings:
                io.write_line(
                    "  <fg=yellow;options=bold>•</> <warning>{}</warning>".format(
                        warning
                    )
                )

        return True

    def _get_message(
        self, poetry: "Poetry", path: "Path", done: bool = False, error: bool = False
    ) -> str:
        operation_color = "blue"

        if error:
            operation_color = "red"
        elif done:
            operation_color = "green"

        verb = "Bundling"
        if done:
            verb = "<success>Bundled</success>"

        return "  <fg={};options=bold>•</> {} <c1>{}</c1> (<b>{}</b>) into <c2>{}</c2>".format(
            operation_color,
            verb,
            poetry.package.pretty_name,
            poetry.package.pretty_version,
            path,
        )

    def _write(self, io: "IO", message: str) -> None:
        from cleo.io.outputs.section_output import SectionOutput  # noqa

        if io.is_debug() or not io.is_decorated() or not isinstance(io, SectionOutput):
            io.write_line(message)
            return

        io = cast(SectionOutput, io)
        io.overwrite(message)
