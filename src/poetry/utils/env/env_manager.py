from __future__ import annotations

import base64
import hashlib
import os
import plistlib
import re
import shutil
import subprocess
import sys

from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING

import tomlkit
import virtualenv

from cleo.io.null_io import NullIO
from cleo.io.outputs.output import Verbosity
from poetry.core.constraints.version import Version
from poetry.core.constraints.version import parse_constraint

from poetry.toml.file import TOMLFile
from poetry.utils._compat import WINDOWS
from poetry.utils._compat import encode
from poetry.utils.env.exceptions import EnvCommandError
from poetry.utils.env.exceptions import IncorrectEnvError
from poetry.utils.env.exceptions import InvalidCurrentPythonVersionError
from poetry.utils.env.exceptions import NoCompatiblePythonVersionFound
from poetry.utils.env.exceptions import PythonVersionNotFound
from poetry.utils.env.generic_env import GenericEnv
from poetry.utils.env.script_strings import GET_ENV_PATH_ONELINER
from poetry.utils.env.script_strings import GET_PYTHON_VERSION_ONELINER
from poetry.utils.env.system_env import SystemEnv
from poetry.utils.env.virtual_env import VirtualEnv
from poetry.utils.helpers import get_real_windows_path
from poetry.utils.helpers import remove_directory


if TYPE_CHECKING:
    from cleo.io.io import IO

    from poetry.poetry import Poetry
    from poetry.utils.env.base_env import Env


class EnvManager:
    """
    Environments manager
    """

    _env = None

    ENVS_FILE = "envs.toml"

    def __init__(self, poetry: Poetry, io: None | IO = None) -> None:
        self._poetry = poetry
        self._io = io or NullIO()

    @staticmethod
    def _full_python_path(python: str) -> Path | None:
        # eg first find pythonXY.bat on windows.
        path_python = shutil.which(python)
        if path_python is None:
            return None

        try:
            executable = subprocess.check_output(
                [path_python, "-c", "import sys; print(sys.executable)"], text=True
            ).strip()
            return Path(executable)

        except CalledProcessError:
            return None

    @staticmethod
    def _detect_active_python(io: None | IO = None) -> Path | None:
        io = io or NullIO()
        io.write_error_line(
            "Trying to detect current active python executable as specified in"
            " the config.",
            verbosity=Verbosity.VERBOSE,
        )

        executable = EnvManager._full_python_path("python")

        if executable is not None:
            io.write_error_line(f"Found: {executable}", verbosity=Verbosity.VERBOSE)
        else:
            io.write_error_line(
                "Unable to detect the current active python executable. Falling"
                " back to default.",
                verbosity=Verbosity.VERBOSE,
            )

        return executable

    @staticmethod
    def get_python_version(
        precision: int = 3,
        prefer_active_python: bool = False,
        io: None | IO = None,
    ) -> Version:
        version = ".".join(str(v) for v in sys.version_info[:precision])

        if prefer_active_python:
            executable = EnvManager._detect_active_python(io)

            if executable:
                python_patch = subprocess.check_output(
                    [executable, "-c", GET_PYTHON_VERSION_ONELINER], text=True
                ).strip()

                version = ".".join(str(v) for v in python_patch.split(".")[:precision])

        return Version.parse(version)

    @property
    def in_project_venv(self) -> Path:
        venv: Path = self._poetry.file.path.parent / ".venv"
        return venv

    def activate(self, python: str) -> Env:
        venv_path = self._poetry.config.virtualenvs_path
        cwd = self._poetry.file.path.parent

        envs_file = TOMLFile(venv_path / self.ENVS_FILE)

        try:
            python_version = Version.parse(python)
            python = f"python{python_version.major}"
            if python_version.precision > 1:
                python += f".{python_version.minor}"
        except ValueError:
            # Executable in PATH or full executable path
            pass

        python_path = self._full_python_path(python)
        if python_path is None:
            raise PythonVersionNotFound(python)

        try:
            python_version_string = subprocess.check_output(
                [python_path, "-c", GET_PYTHON_VERSION_ONELINER], text=True
            )
        except CalledProcessError as e:
            raise EnvCommandError(e)

        python_version = Version.parse(python_version_string.strip())
        minor = f"{python_version.major}.{python_version.minor}"
        patch = python_version.text

        create = False
        # If we are required to create the virtual environment in the project directory,
        # create or recreate it if needed
        if self.use_in_project_venv():
            create = False
            venv = self.in_project_venv
            if venv.exists():
                # We need to check if the patch version is correct
                _venv = VirtualEnv(venv)
                current_patch = ".".join(str(v) for v in _venv.version_info[:3])

                if patch != current_patch:
                    create = True

            self.create_venv(executable=python_path, force=create)

            return self.get(reload=True)

        envs = tomlkit.document()
        base_env_name = self.generate_env_name(self._poetry.package.name, str(cwd))
        if envs_file.exists():
            envs = envs_file.read()
            current_env = envs.get(base_env_name)
            if current_env is not None:
                current_minor = current_env["minor"]
                current_patch = current_env["patch"]

                if current_minor == minor and current_patch != patch:
                    # We need to recreate
                    create = True

        name = f"{base_env_name}-py{minor}"
        venv = venv_path / name

        # Create if needed
        if not venv.exists() or venv.exists() and create:
            in_venv = os.environ.get("VIRTUAL_ENV") is not None
            if in_venv or not venv.exists():
                create = True

            if venv.exists():
                # We need to check if the patch version is correct
                _venv = VirtualEnv(venv)
                current_patch = ".".join(str(v) for v in _venv.version_info[:3])

                if patch != current_patch:
                    create = True

            self.create_venv(executable=python_path, force=create)

        # Activate
        envs[base_env_name] = {"minor": minor, "patch": patch}
        envs_file.write(envs)

        return self.get(reload=True)

    def deactivate(self) -> None:
        venv_path = self._poetry.config.virtualenvs_path
        name = self.generate_env_name(
            self._poetry.package.name, str(self._poetry.file.path.parent)
        )

        envs_file = TOMLFile(venv_path / self.ENVS_FILE)
        if envs_file.exists():
            envs = envs_file.read()
            env = envs.get(name)
            if env is not None:
                venv = venv_path / f"{name}-py{env['minor']}"
                self._io.write_error_line(
                    f"Deactivating virtualenv: <comment>{venv}</comment>"
                )
                del envs[name]

                envs_file.write(envs)

    def get(self, reload: bool = False) -> Env:
        if self._env is not None and not reload:
            return self._env

        prefer_active_python = self._poetry.config.get(
            "virtualenvs.prefer-active-python"
        )
        python_minor = self.get_python_version(
            precision=2, prefer_active_python=prefer_active_python, io=self._io
        ).to_string()

        venv_path = self._poetry.config.virtualenvs_path

        cwd = self._poetry.file.path.parent
        envs_file = TOMLFile(venv_path / self.ENVS_FILE)
        env = None
        base_env_name = self.generate_env_name(self._poetry.package.name, str(cwd))
        if envs_file.exists():
            envs = envs_file.read()
            env = envs.get(base_env_name)
            if env:
                python_minor = env["minor"]

        # Check if we are inside a virtualenv or not
        # Conda sets CONDA_PREFIX in its envs, see
        # https://github.com/conda/conda/issues/2764
        env_prefix = os.environ.get("VIRTUAL_ENV", os.environ.get("CONDA_PREFIX"))
        conda_env_name = os.environ.get("CONDA_DEFAULT_ENV")
        # It's probably not a good idea to pollute Conda's global "base" env, since
        # most users have it activated all the time.
        in_venv = env_prefix is not None and conda_env_name != "base"

        if not in_venv or env is not None:
            # Checking if a local virtualenv exists
            if self.in_project_venv_exists():
                venv = self.in_project_venv

                return VirtualEnv(venv)

            create_venv = self._poetry.config.get("virtualenvs.create", True)

            if not create_venv:
                return self.get_system_env()

            venv_path = self._poetry.config.virtualenvs_path

            name = f"{base_env_name}-py{python_minor.strip()}"

            venv = venv_path / name

            if not venv.exists():
                return self.get_system_env()

            return VirtualEnv(venv)

        if env_prefix is not None:
            prefix = Path(env_prefix)
            base_prefix = None
        else:
            prefix = Path(sys.prefix)
            base_prefix = self.get_base_prefix()

        return VirtualEnv(prefix, base_prefix)

    def list(self, name: str | None = None) -> list[VirtualEnv]:
        if name is None:
            name = self._poetry.package.name

        venv_name = self.generate_env_name(name, str(self._poetry.file.path.parent))
        venv_path = self._poetry.config.virtualenvs_path
        env_list = [VirtualEnv(p) for p in sorted(venv_path.glob(f"{venv_name}-py*"))]

        if self.in_project_venv_exists():
            venv = self.in_project_venv
            env_list.insert(0, VirtualEnv(venv))
        return env_list

    @staticmethod
    def check_env_is_for_current_project(env: str, base_env_name: str) -> bool:
        """
        Check if env name starts with projects name.

        This is done to prevent action on other project's envs.
        """
        return env.startswith(base_env_name)

    def remove(self, python: str) -> Env:
        venv_path = self._poetry.config.virtualenvs_path

        cwd = self._poetry.file.path.parent
        envs_file = TOMLFile(venv_path / self.ENVS_FILE)
        base_env_name = self.generate_env_name(self._poetry.package.name, str(cwd))

        python_path = Path(python)
        if python_path.is_file():
            # Validate env name if provided env is a full path to python
            try:
                env_dir = subprocess.check_output(
                    [python, "-c", GET_ENV_PATH_ONELINER], text=True
                ).strip("\n")
                env_name = Path(env_dir).name
                if not self.check_env_is_for_current_project(env_name, base_env_name):
                    raise IncorrectEnvError(env_name)
            except CalledProcessError as e:
                raise EnvCommandError(e)

        if self.check_env_is_for_current_project(python, base_env_name):
            venvs = self.list()
            for venv in venvs:
                if venv.path.name == python:
                    # Exact virtualenv name
                    if not envs_file.exists():
                        self.remove_venv(venv.path)

                        return venv

                    venv_minor = ".".join(str(v) for v in venv.version_info[:2])
                    base_env_name = self.generate_env_name(cwd.name, str(cwd))
                    envs = envs_file.read()

                    current_env = envs.get(base_env_name)
                    if not current_env:
                        self.remove_venv(venv.path)

                        return venv

                    if current_env["minor"] == venv_minor:
                        del envs[base_env_name]
                        envs_file.write(envs)

                    self.remove_venv(venv.path)

                    return venv

            raise ValueError(
                f'<warning>Environment "{python}" does not exist.</warning>'
            )
        else:
            venv_path = self._poetry.config.virtualenvs_path
            # Get all the poetry envs, even for other projects
            env_names = [p.name for p in sorted(venv_path.glob("*-*-py*"))]
            if python in env_names:
                raise IncorrectEnvError(python)

        try:
            python_version = Version.parse(python)
            python = f"python{python_version.major}"
            if python_version.precision > 1:
                python += f".{python_version.minor}"
        except ValueError:
            # Executable in PATH or full executable path
            pass

        try:
            python_version_string = subprocess.check_output(
                [python, "-c", GET_PYTHON_VERSION_ONELINER], text=True
            )
        except CalledProcessError as e:
            raise EnvCommandError(e)

        python_version = Version.parse(python_version_string.strip())
        minor = f"{python_version.major}.{python_version.minor}"

        name = f"{base_env_name}-py{minor}"
        venv_path = venv_path / name

        if not venv_path.exists():
            raise ValueError(f'<warning>Environment "{name}" does not exist.</warning>')

        if envs_file.exists():
            envs = envs_file.read()
            current_env = envs.get(base_env_name)
            if current_env is not None:
                current_minor = current_env["minor"]

                if current_minor == minor:
                    del envs[base_env_name]
                    envs_file.write(envs)

        self.remove_venv(venv_path)

        return VirtualEnv(venv_path, venv_path)

    def use_in_project_venv(self) -> bool:
        in_project: bool | None = self._poetry.config.get("virtualenvs.in-project")
        if in_project is not None:
            return in_project

        return self.in_project_venv.is_dir()

    def in_project_venv_exists(self) -> bool:
        in_project: bool | None = self._poetry.config.get("virtualenvs.in-project")
        if in_project is False:
            return False

        return self.in_project_venv.is_dir()

    def create_venv(
        self,
        name: str | None = None,
        executable: Path | None = None,
        force: bool = False,
    ) -> Env:
        if self._env is not None and not force:
            return self._env

        cwd = self._poetry.file.path.parent
        env = self.get(reload=True)

        if not env.is_sane():
            force = True

        if env.is_venv() and not force:
            # Already inside a virtualenv.
            current_python = Version.parse(
                ".".join(str(c) for c in env.version_info[:3])
            )
            if not self._poetry.package.python_constraint.allows(current_python):
                raise InvalidCurrentPythonVersionError(
                    self._poetry.package.python_versions, str(current_python)
                )
            return env

        create_venv = self._poetry.config.get("virtualenvs.create")
        in_project_venv = self.use_in_project_venv()
        prefer_active_python = self._poetry.config.get(
            "virtualenvs.prefer-active-python"
        )
        venv_prompt = self._poetry.config.get("virtualenvs.prompt")

        if not executable and prefer_active_python:
            executable = self._detect_active_python()

        venv_path = (
            self.in_project_venv
            if in_project_venv
            else self._poetry.config.virtualenvs_path
        )
        if not name:
            name = self._poetry.package.name

        python_patch = ".".join([str(v) for v in sys.version_info[:3]])
        python_minor = ".".join([str(v) for v in sys.version_info[:2]])
        if executable:
            python_patch = subprocess.check_output(
                [executable, "-c", GET_PYTHON_VERSION_ONELINER], text=True
            ).strip()
            python_minor = ".".join(python_patch.split(".")[:2])

        supported_python = self._poetry.package.python_constraint
        if not supported_python.allows(Version.parse(python_patch)):
            # The currently activated or chosen Python version
            # is not compatible with the Python constraint specified
            # for the project.
            # If an executable has been specified, we stop there
            # and notify the user of the incompatibility.
            # Otherwise, we try to find a compatible Python version.
            if executable and not prefer_active_python:
                raise NoCompatiblePythonVersionFound(
                    self._poetry.package.python_versions, python_patch
                )

            self._io.write_error_line(
                f"<warning>The currently activated Python version {python_patch} is not"
                f" supported by the project ({self._poetry.package.python_versions}).\n"
                "Trying to find and use a compatible version.</warning> "
            )

            for suffix in sorted(
                self._poetry.package.AVAILABLE_PYTHONS,
                key=lambda v: (v.startswith("3"), -len(v), v),
                reverse=True,
            ):
                if len(suffix) == 1:
                    if not parse_constraint(f"^{suffix}.0").allows_any(
                        supported_python
                    ):
                        continue
                elif not supported_python.allows_any(parse_constraint(suffix + ".*")):
                    continue

                python_name = f"python{suffix}"
                if self._io.is_debug():
                    self._io.write_error_line(f"<debug>Trying {python_name}</debug>")

                python = self._full_python_path(python_name)
                if python is None:
                    continue

                try:
                    python_patch = subprocess.check_output(
                        [python, "-c", GET_PYTHON_VERSION_ONELINER],
                        stderr=subprocess.STDOUT,
                        text=True,
                    ).strip()
                except CalledProcessError:
                    continue

                if supported_python.allows(Version.parse(python_patch)):
                    self._io.write_error_line(
                        f"Using <c1>{python_name}</c1> ({python_patch})"
                    )
                    executable = python
                    python_minor = ".".join(python_patch.split(".")[:2])
                    break

            if not executable:
                raise NoCompatiblePythonVersionFound(
                    self._poetry.package.python_versions
                )

        if in_project_venv:
            venv = venv_path
        else:
            name = self.generate_env_name(name, str(cwd))
            name = f"{name}-py{python_minor.strip()}"
            venv = venv_path / name

        if venv_prompt is not None:
            venv_prompt = venv_prompt.format(
                project_name=self._poetry.package.name or "virtualenv",
                python_version=python_minor,
            )

        if not venv.exists():
            if create_venv is False:
                self._io.write_error_line(
                    "<fg=black;bg=yellow>"
                    "Skipping virtualenv creation, "
                    "as specified in config file."
                    "</>"
                )

                return self.get_system_env()

            self._io.write_error_line(
                f"Creating virtualenv <c1>{name}</> in"
                f" {venv_path if not WINDOWS else get_real_windows_path(venv_path)!s}"
            )
        else:
            create_venv = False
            if force:
                if not env.is_sane():
                    self._io.write_error_line(
                        f"<warning>The virtual environment found in {env.path} seems to"
                        " be broken.</warning>"
                    )
                self._io.write_error_line(
                    f"Recreating virtualenv <c1>{name}</> in {venv!s}"
                )
                self.remove_venv(venv)
                create_venv = True
            elif self._io.is_very_verbose():
                self._io.write_error_line(f"Virtualenv <c1>{name}</> already exists.")

        if create_venv:
            self.build_venv(
                venv,
                executable=executable,
                flags=self._poetry.config.get("virtualenvs.options"),
                prompt=venv_prompt,
            )

        # venv detection:
        # stdlib venv may symlink sys.executable, so we can't use realpath.
        # but others can symlink *to* the venv Python,
        # so we can't just use sys.executable.
        # So we just check every item in the symlink tree (generally <= 3)
        p = os.path.normcase(sys.executable)
        paths = [p]
        while os.path.islink(p):
            p = os.path.normcase(os.path.join(os.path.dirname(p), os.readlink(p)))
            paths.append(p)

        p_venv = os.path.normcase(str(venv))
        if any(p.startswith(p_venv) for p in paths):
            # Running properly in the virtualenv, don't need to do anything
            return self.get_system_env()

        return VirtualEnv(venv)

    @classmethod
    def build_venv(
        cls,
        path: Path,
        executable: Path | None = None,
        flags: dict[str, bool] | None = None,
        with_pip: bool | None = None,
        with_wheel: bool | None = None,
        with_setuptools: bool | None = None,
        prompt: str | None = None,
    ) -> virtualenv.run.session.Session:
        if WINDOWS:
            path = get_real_windows_path(path)
            executable = get_real_windows_path(executable) if executable else None

        flags = flags or {}

        flags["no-pip"] = (
            not with_pip if with_pip is not None else flags.pop("no-pip", True)
        )

        flags["no-setuptools"] = (
            not with_setuptools
            if with_setuptools is not None
            else flags.pop("no-setuptools", True)
        )

        # we want wheels to be enabled when pip is required and it has not been
        # explicitly disabled
        flags["no-wheel"] = (
            not with_wheel
            if with_wheel is not None
            else flags.pop("no-wheel", flags["no-pip"])
        )

        executable_str = None if executable is None else executable.resolve().as_posix()

        args = [
            "--no-download",
            "--no-periodic-update",
            "--python",
            executable_str or sys.executable,
        ]

        if prompt is not None:
            args.extend(["--prompt", prompt])

        for flag, value in flags.items():
            if value is True:
                args.append(f"--{flag}")

        args.append(str(path))

        cli_result = virtualenv.cli_run(args)

        # Exclude the venv folder from from macOS Time Machine backups
        # TODO: Add backup-ignore markers for other platforms too
        if sys.platform == "darwin":
            import xattr

            xattr.setxattr(
                str(path),
                "com.apple.metadata:com_apple_backup_excludeItem",
                plistlib.dumps("com.apple.backupd", fmt=plistlib.FMT_BINARY),
            )

        return cli_result

    @classmethod
    def remove_venv(cls, path: Path) -> None:
        assert path.is_dir()
        try:
            remove_directory(path)
            return
        except OSError as e:
            # Continue only if e.errno == 16
            if e.errno != 16:  # ERRNO 16: Device or resource busy
                raise e

        # Delete all files and folders but the toplevel one. This is because sometimes
        # the venv folder is mounted by the OS, such as in a docker volume. In such
        # cases, an attempt to delete the folder itself will result in an `OSError`.
        # See https://github.com/python-poetry/poetry/pull/2064
        for file_path in path.iterdir():
            if file_path.is_file() or file_path.is_symlink():
                file_path.unlink()
            elif file_path.is_dir():
                remove_directory(file_path, force=True)

    @classmethod
    def get_system_env(cls, naive: bool = False) -> Env:
        """
        Retrieve the current Python environment.

        This can be the base Python environment or an activated virtual environment.

        This method also workaround the issue that the virtual environment
        used by Poetry internally (when installed via the custom installer)
        is incorrectly detected as the system environment. Note that this workaround
        happens only when `naive` is False since there are times where we actually
        want to retrieve Poetry's custom virtual environment
        (e.g. plugin installation or self update).
        """
        prefix, base_prefix = Path(sys.prefix), Path(cls.get_base_prefix())
        env: Env = SystemEnv(prefix)
        if not naive:
            if prefix.joinpath("poetry_env").exists():
                env = GenericEnv(base_prefix, child_env=env)
            else:
                from poetry.locations import data_dir

                try:
                    prefix.relative_to(data_dir())
                except ValueError:
                    pass
                else:
                    env = GenericEnv(base_prefix, child_env=env)

        return env

    @classmethod
    def get_base_prefix(cls) -> Path:
        real_prefix = getattr(sys, "real_prefix", None)
        if real_prefix is not None:
            return Path(real_prefix)

        base_prefix = getattr(sys, "base_prefix", None)
        if base_prefix is not None:
            return Path(base_prefix)

        return Path(sys.prefix)

    @classmethod
    def generate_env_name(cls, name: str, cwd: str) -> str:
        name = name.lower()
        sanitized_name = re.sub(r'[ $`!*@"\\\r\n\t]', "_", name)[:42]
        normalized_cwd = os.path.normcase(os.path.realpath(cwd))
        h_bytes = hashlib.sha256(encode(normalized_cwd)).digest()
        h_str = base64.urlsafe_b64encode(h_bytes).decode()[:8]

        return f"{sanitized_name}-{h_str}"
