import base64
import hashlib
import itertools
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import sysconfig
import textwrap

from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from subprocess import CalledProcessError
from typing import Any
from typing import ContextManager
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import packaging.tags
import tomlkit
import virtualenv

from cleo.io.io import IO
from packaging.tags import Tag
from packaging.tags import interpreter_name
from packaging.tags import interpreter_version
from packaging.tags import sys_tags
from virtualenv.seed.wheels.embed import get_embed_wheel

from poetry.core.semver.helpers import parse_constraint
from poetry.core.semver.version import Version
from poetry.core.toml.file import TOMLFile
from poetry.core.version.markers import BaseMarker
from poetry.locations import CACHE_DIR
from poetry.poetry import Poetry
from poetry.utils._compat import decode
from poetry.utils._compat import encode
from poetry.utils._compat import list_to_shell_command
from poetry.utils._compat import metadata
from poetry.utils.helpers import is_dir_writable
from poetry.utils.helpers import paths_csv
from poetry.utils.helpers import temporary_directory


GET_ENVIRONMENT_INFO = """\
import json
import os
import platform
import sys
import sysconfig

INTERPRETER_SHORT_NAMES = {
    "python": "py",
    "cpython": "cp",
    "pypy": "pp",
    "ironpython": "ip",
    "jython": "jy",
}


def interpreter_version():
    version = sysconfig.get_config_var("interpreter_version")
    if version:
        version = str(version)
    else:
        version = _version_nodot(sys.version_info[:2])

    return version


def _version_nodot(version):
    # type: (PythonVersion) -> str
    if any(v >= 10 for v in version):
        sep = "_"
    else:
        sep = ""

    return sep.join(map(str, version))


if hasattr(sys, "implementation"):
    info = sys.implementation.version
    iver = "{0.major}.{0.minor}.{0.micro}".format(info)
    kind = info.releaselevel
    if kind != "final":
        iver += kind[0] + str(info.serial)

    implementation_name = sys.implementation.name
else:
    iver = "0"
    implementation_name = platform.python_implementation().lower()

env = {
    "implementation_name": implementation_name,
    "implementation_version": iver,
    "os_name": os.name,
    "platform_machine": platform.machine(),
    "platform_release": platform.release(),
    "platform_system": platform.system(),
    "platform_version": platform.version(),
    "python_full_version": platform.python_version(),
    "platform_python_implementation": platform.python_implementation(),
    "python_version": ".".join(platform.python_version_tuple()[:2]),
    "sys_platform": sys.platform,
    "version_info": tuple(sys.version_info),
    # Extra information
    "interpreter_name": INTERPRETER_SHORT_NAMES.get(implementation_name, implementation_name),
    "interpreter_version": interpreter_version(),
}

print(json.dumps(env))
"""


GET_BASE_PREFIX = """\
import sys

if hasattr(sys, "real_prefix"):
    print(sys.real_prefix)
elif hasattr(sys, "base_prefix"):
    print(sys.base_prefix)
else:
    print(sys.prefix)
"""

GET_PYTHON_VERSION = """\
import sys

print('.'.join([str(s) for s in sys.version_info[:3]]))
"""

GET_SYS_PATH = """\
import json
import sys

print(json.dumps(sys.path))
"""

GET_PATHS = """\
import json
import sysconfig

print(json.dumps(sysconfig.get_paths()))
"""


class SitePackages:
    def __init__(
        self,
        purelib: Path,
        platlib: Optional[Path] = None,
        fallbacks: List[Path] = None,
        skip_write_checks: bool = False,
    ) -> None:
        self._purelib = purelib
        self._platlib = platlib or purelib

        if platlib and platlib.resolve() == purelib.resolve():
            self._platlib = purelib

        self._fallbacks = fallbacks or []
        self._skip_write_checks = skip_write_checks

        self._candidates: List[Path] = []
        for path in itertools.chain([self._purelib, self._platlib], self._fallbacks):
            if path not in self._candidates:
                self._candidates.append(path)

        self._writable_candidates = None if not skip_write_checks else self._candidates

    @property
    def path(self) -> Path:
        return self._purelib

    @property
    def purelib(self) -> Path:
        return self._purelib

    @property
    def platlib(self) -> Path:
        return self._platlib

    @property
    def candidates(self) -> List[Path]:
        return self._candidates

    @property
    def writable_candidates(self) -> List[Path]:
        if self._writable_candidates is not None:
            return self._writable_candidates

        self._writable_candidates = []
        for candidate in self._candidates:
            if not is_dir_writable(path=candidate, create=True):
                continue
            self._writable_candidates.append(candidate)

        return self._writable_candidates

    def make_candidates(
        self, path: Path, writable_only: bool = False, strict: bool = False
    ) -> List[Path]:
        candidates = self._candidates if not writable_only else self.writable_candidates
        if path.is_absolute():
            for candidate in candidates:
                try:
                    path.relative_to(candidate)
                    return [path]
                except ValueError:
                    pass
            else:
                raise ValueError(
                    "{} is not relative to any discovered {}sites".format(
                        path, "writable " if writable_only else ""
                    )
                )

        results = [candidate / path for candidate in candidates if candidate]

        if not results and strict:
            raise RuntimeError(
                'Unable to find a suitable destination for "{}" in {}'.format(
                    str(path), paths_csv(self._candidates)
                )
            )

        return results

    def distributions(
        self, name: Optional[str] = None, writable_only: bool = False
    ) -> Iterable[metadata.PathDistribution]:
        path = list(
            map(
                str, self._candidates if not writable_only else self.writable_candidates
            )
        )
        for distribution in metadata.PathDistribution.discover(
            name=name, path=path
        ):  # type: metadata.PathDistribution
            yield distribution

    def find_distribution(
        self, name: str, writable_only: bool = False
    ) -> Optional[metadata.PathDistribution]:
        for distribution in self.distributions(name=name, writable_only=writable_only):
            return distribution
        else:
            return None

    def find_distribution_files_with_suffix(
        self, distribution_name: str, suffix: str, writable_only: bool = False
    ) -> Iterable[Path]:
        for distribution in self.distributions(
            name=distribution_name, writable_only=writable_only
        ):
            for file in distribution.files:
                if file.name.endswith(suffix):
                    yield Path(distribution.locate_file(file))

    def find_distribution_files_with_name(
        self, distribution_name: str, name: str, writable_only: bool = False
    ) -> Iterable[Path]:
        for distribution in self.distributions(
            name=distribution_name, writable_only=writable_only
        ):
            for file in distribution.files:
                if file.name == name:
                    yield Path(distribution.locate_file(file))

    def find_distribution_nspkg_pth_files(
        self, distribution_name: str, writable_only: bool = False
    ) -> Iterable[Path]:
        return self.find_distribution_files_with_suffix(
            distribution_name=distribution_name,
            suffix="-nspkg.pth",
            writable_only=writable_only,
        )

    def find_distribution_direct_url_json_files(
        self, distribution_name: str, writable_only: bool = False
    ) -> Iterable[Path]:
        return self.find_distribution_files_with_name(
            distribution_name=distribution_name,
            name="direct_url.json",
            writable_only=writable_only,
        )

    def remove_distribution_files(self, distribution_name: str) -> List[Path]:
        paths = []

        for distribution in self.distributions(
            name=distribution_name, writable_only=True
        ):
            for file in distribution.files:
                file = Path(distribution.locate_file(file))
                # We can't use unlink(missing_ok=True) because it's not always available
                if file.exists():
                    file.unlink()

            if distribution._path.exists():
                shutil.rmtree(str(distribution._path))

            paths.append(distribution._path)

        return paths

    def _path_method_wrapper(
        self,
        path: Union[str, Path],
        method: str,
        *args: Any,
        return_first: bool = True,
        writable_only: bool = False,
        **kwargs: Any,
    ) -> Union[Tuple[Path, Any], List[Tuple[Path, Any]]]:
        if isinstance(path, str):
            path = Path(path)

        candidates = self.make_candidates(
            path, writable_only=writable_only, strict=True
        )

        results = []

        for candidate in candidates:
            try:
                result = candidate, getattr(candidate, method)(*args, **kwargs)
                if return_first:
                    return result
                results.append(result)
            except OSError:
                # TODO: Replace with PermissionError
                pass

        if results:
            return results

        raise OSError("Unable to access any of {}".format(paths_csv(candidates)))

    def write_text(self, path: Union[str, Path], *args: Any, **kwargs: Any) -> Path:
        return self._path_method_wrapper(path, "write_text", *args, **kwargs)[0]

    def mkdir(self, path: Union[str, Path], *args: Any, **kwargs: Any) -> Path:
        return self._path_method_wrapper(path, "mkdir", *args, **kwargs)[0]

    def exists(self, path: Union[str, Path]) -> bool:
        return any(
            value[-1]
            for value in self._path_method_wrapper(path, "exists", return_first=False)
        )

    def find(
        self,
        path: Union[str, Path],
        writable_only: bool = False,
    ) -> List[Path]:
        return [
            value[0]
            for value in self._path_method_wrapper(
                path, "exists", return_first=False, writable_only=writable_only
            )
            if value[-1] is True
        ]

    def __getattr__(self, item: str) -> Any:
        try:
            return super().__getattribute__(item)
        except AttributeError:
            return getattr(self.path, item)


class EnvError(Exception):

    pass


class EnvCommandError(EnvError):
    def __init__(self, e: CalledProcessError, input: Optional[str] = None) -> None:
        self.e = e

        message = "Command {} errored with the following return code {}, and output: \n{}".format(
            e.cmd, e.returncode, decode(e.output)
        )
        if input:
            message += f"input was : {input}"
        super().__init__(message)


class NoCompatiblePythonVersionFound(EnvError):
    def __init__(self, expected: str, given: Optional[str] = None) -> None:
        if given:
            message = (
                "The specified Python version ({}) "
                "is not supported by the project ({}).\n"
                "Please choose a compatible version "
                "or loosen the python constraint specified "
                "in the pyproject.toml file.".format(given, expected)
            )
        else:
            message = (
                "Poetry was unable to find a compatible version. "
                "If you have one, you can explicitly use it "
                'via the "env use" command.'
            )

        super().__init__(message)


class EnvManager:
    """
    Environments manager
    """

    _env = None

    ENVS_FILE = "envs.toml"

    def __init__(self, poetry: Poetry) -> None:
        self._poetry = poetry

    def activate(self, python: str, io: IO) -> "Env":
        venv_path = self._poetry.config.get("virtualenvs.path")
        if venv_path is None:
            venv_path = Path(CACHE_DIR) / "virtualenvs"
        else:
            venv_path = Path(venv_path)

        cwd = self._poetry.file.parent

        envs_file = TOMLFile(venv_path / self.ENVS_FILE)

        try:
            python_version = Version.parse(python)
            python = f"python{python_version.major}"
            if python_version.precision > 1:
                python += f".{python_version.minor}"
        except ValueError:
            # Executable in PATH or full executable path
            pass

        try:
            python_version = decode(
                subprocess.check_output(
                    list_to_shell_command(
                        [
                            python,
                            "-c",
                            "\"import sys; print('.'.join([str(s) for s in sys.version_info[:3]]))\"",
                        ]
                    ),
                    shell=True,
                )
            )
        except CalledProcessError as e:
            raise EnvCommandError(e)

        python_version = Version.parse(python_version.strip())
        minor = f"{python_version.major}.{python_version.minor}"
        patch = python_version.text

        create = False
        is_root_venv = self._poetry.config.get("virtualenvs.in-project")
        # If we are required to create the virtual environment in the root folder,
        # create or recreate it if needed
        if is_root_venv:
            create = False
            venv = self._poetry.file.parent / ".venv"
            if venv.exists():
                # We need to check if the patch version is correct
                _venv = VirtualEnv(venv)
                current_patch = ".".join(str(v) for v in _venv.version_info[:3])

                if patch != current_patch:
                    create = True

            self.create_venv(io, executable=python, force=create)

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

            self.create_venv(io, executable=python, force=create)

        # Activate
        envs[base_env_name] = {"minor": minor, "patch": patch}
        envs_file.write(envs)

        return self.get(reload=True)

    def deactivate(self, io: IO) -> None:
        venv_path = self._poetry.config.get("virtualenvs.path")
        if venv_path is None:
            venv_path = Path(CACHE_DIR) / "virtualenvs"
        else:
            venv_path = Path(venv_path)

        name = self._poetry.package.name
        name = self.generate_env_name(name, str(self._poetry.file.parent))

        envs_file = TOMLFile(venv_path / self.ENVS_FILE)
        if envs_file.exists():
            envs = envs_file.read()
            env = envs.get(name)
            if env is not None:
                io.write_line(
                    "Deactivating virtualenv: <comment>{}</comment>".format(
                        venv_path / (name + "-py{}".format(env["minor"]))
                    )
                )
                del envs[name]

                envs_file.write(envs)

    def get(self, reload: bool = False) -> Union["VirtualEnv", "SystemEnv"]:
        if self._env is not None and not reload:
            return self._env

        python_minor = ".".join([str(v) for v in sys.version_info[:2]])

        venv_path = self._poetry.config.get("virtualenvs.path")
        if venv_path is None:
            venv_path = Path(CACHE_DIR) / "virtualenvs"
        else:
            venv_path = Path(venv_path)

        cwd = self._poetry.file.parent
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
            if self._poetry.config.get("virtualenvs.in-project") is not False:
                if (cwd / ".venv").exists() and (cwd / ".venv").is_dir():
                    venv = cwd / ".venv"

                    return VirtualEnv(venv)

            create_venv = self._poetry.config.get("virtualenvs.create", True)

            if not create_venv:
                return self.get_system_env()

            venv_path = self._poetry.config.get("virtualenvs.path")
            if venv_path is None:
                venv_path = Path(CACHE_DIR) / "virtualenvs"
            else:
                venv_path = Path(venv_path)

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

    def list(self, name: Optional[str] = None) -> List["VirtualEnv"]:
        if name is None:
            name = self._poetry.package.name

        venv_name = self.generate_env_name(name, str(self._poetry.file.parent))

        venv_path = self._poetry.config.get("virtualenvs.path")
        if venv_path is None:
            venv_path = Path(CACHE_DIR) / "virtualenvs"
        else:
            venv_path = Path(venv_path)

        env_list = [
            VirtualEnv(Path(p)) for p in sorted(venv_path.glob(f"{venv_name}-py*"))
        ]

        venv = self._poetry.file.parent / ".venv"
        if (
            self._poetry.config.get("virtualenvs.in-project")
            and venv.exists()
            and venv.is_dir()
        ):
            env_list.insert(0, VirtualEnv(venv))
        return env_list

    def remove(self, python: str) -> "Env":
        venv_path = self._poetry.config.get("virtualenvs.path")
        if venv_path is None:
            venv_path = Path(CACHE_DIR) / "virtualenvs"
        else:
            venv_path = Path(venv_path)

        cwd = self._poetry.file.parent
        envs_file = TOMLFile(venv_path / self.ENVS_FILE)
        base_env_name = self.generate_env_name(self._poetry.package.name, str(cwd))

        if python.startswith(base_env_name):
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

        try:
            python_version = Version.parse(python)
            python = f"python{python_version.major}"
            if python_version.precision > 1:
                python += f".{python_version.minor}"
        except ValueError:
            # Executable in PATH or full executable path
            pass

        try:
            python_version = decode(
                subprocess.check_output(
                    list_to_shell_command(
                        [
                            python,
                            "-c",
                            "\"import sys; print('.'.join([str(s) for s in sys.version_info[:3]]))\"",
                        ]
                    ),
                    shell=True,
                )
            )
        except CalledProcessError as e:
            raise EnvCommandError(e)

        python_version = Version.parse(python_version.strip())
        minor = f"{python_version.major}.{python_version.minor}"

        name = f"{base_env_name}-py{minor}"
        venv = venv_path / name

        if not venv.exists():
            raise ValueError(f'<warning>Environment "{name}" does not exist.</warning>')

        if envs_file.exists():
            envs = envs_file.read()
            current_env = envs.get(base_env_name)
            if current_env is not None:
                current_minor = current_env["minor"]

                if current_minor == minor:
                    del envs[base_env_name]
                    envs_file.write(envs)

        self.remove_venv(venv)

        return VirtualEnv(venv)

    def create_venv(
        self,
        io: IO,
        name: Optional[str] = None,
        executable: Optional[str] = None,
        force: bool = False,
    ) -> Union["SystemEnv", "VirtualEnv"]:
        if self._env is not None and not force:
            return self._env

        cwd = self._poetry.file.parent
        env = self.get(reload=True)

        if not env.is_sane():
            force = True

        if env.is_venv() and not force:
            # Already inside a virtualenv.
            return env

        create_venv = self._poetry.config.get("virtualenvs.create")
        root_venv = self._poetry.config.get("virtualenvs.in-project")
        venv_path = self._poetry.config.get("virtualenvs.path")

        if root_venv:
            venv_path = cwd / ".venv"
        elif venv_path is None:
            venv_path = Path(CACHE_DIR) / "virtualenvs"
        else:
            venv_path = Path(venv_path)

        if not name:
            name = self._poetry.package.name

        python_patch = ".".join([str(v) for v in sys.version_info[:3]])
        python_minor = ".".join([str(v) for v in sys.version_info[:2]])
        if executable:
            python_patch = decode(
                subprocess.check_output(
                    list_to_shell_command(
                        [
                            executable,
                            "-c",
                            "\"import sys; print('.'.join([str(s) for s in sys.version_info[:3]]))\"",
                        ]
                    ),
                    shell=True,
                ).strip()
            )
            python_minor = ".".join(python_patch.split(".")[:2])

        supported_python = self._poetry.package.python_constraint
        if not supported_python.allows(Version.parse(python_patch)):
            # The currently activated or chosen Python version
            # is not compatible with the Python constraint specified
            # for the project.
            # If an executable has been specified, we stop there
            # and notify the user of the incompatibility.
            # Otherwise, we try to find a compatible Python version.
            if executable:
                raise NoCompatiblePythonVersionFound(
                    self._poetry.package.python_versions, python_patch
                )

            io.write_line(
                "<warning>The currently activated Python version {} "
                "is not supported by the project ({}).\n"
                "Trying to find and use a compatible version.</warning> ".format(
                    python_patch, self._poetry.package.python_versions
                )
            )

            for python_to_try in reversed(
                sorted(
                    self._poetry.package.AVAILABLE_PYTHONS,
                    key=lambda v: (v.startswith("3"), -len(v), v),
                )
            ):
                if len(python_to_try) == 1:
                    if not parse_constraint(f"^{python_to_try}.0").allows_any(
                        supported_python
                    ):
                        continue
                elif not supported_python.allows_all(
                    parse_constraint(python_to_try + ".*")
                ):
                    continue

                python = "python" + python_to_try

                if io.is_debug():
                    io.write_line(f"<debug>Trying {python}</debug>")

                try:
                    python_patch = decode(
                        subprocess.check_output(
                            list_to_shell_command(
                                [
                                    python,
                                    "-c",
                                    "\"import sys; print('.'.join([str(s) for s in sys.version_info[:3]]))\"",
                                ]
                            ),
                            stderr=subprocess.STDOUT,
                            shell=True,
                        ).strip()
                    )
                except CalledProcessError:
                    continue

                if not python_patch:
                    continue

                if supported_python.allows(Version.parse(python_patch)):
                    io.write_line(f"Using <c1>{python}</c1> ({python_patch})")
                    executable = python
                    python_minor = ".".join(python_patch.split(".")[:2])
                    break

            if not executable:
                raise NoCompatiblePythonVersionFound(
                    self._poetry.package.python_versions
                )

        if root_venv:
            venv = venv_path
        else:
            name = self.generate_env_name(name, str(cwd))
            name = f"{name}-py{python_minor.strip()}"
            venv = venv_path / name

        if not venv.exists():
            if create_venv is False:
                io.write_line(
                    "<fg=black;bg=yellow>"
                    "Skipping virtualenv creation, "
                    "as specified in config file."
                    "</>"
                )

                return self.get_system_env()

            io.write_line(
                "Creating virtualenv <c1>{}</> in {}".format(name, str(venv_path))
            )
        else:
            create_venv = False
            if force:
                if not env.is_sane():
                    io.write_line(
                        "<warning>The virtual environment found in {} seems to be broken.</warning>".format(
                            env.path
                        )
                    )
                io.write_line(
                    "Recreating virtualenv <c1>{}</> in {}".format(name, str(venv))
                )
                self.remove_venv(venv)
                create_venv = True
            elif io.is_very_verbose():
                io.write_line(f"Virtualenv <c1>{name}</> already exists.")

        if create_venv:
            self.build_venv(
                venv,
                executable=executable,
                flags=self._poetry.config.get("virtualenvs.options"),
                # TODO: in a future version switch remove pip/setuptools/wheel
                # poetry does not need them these exists today to not break developer
                # environment assumptions
                with_pip=True,
                with_setuptools=True,
                with_wheel=True,
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
        path: Union[Path, str],
        executable: Optional[Union[str, Path]] = None,
        flags: Dict[str, bool] = None,
        with_pip: Optional[bool] = None,
        with_wheel: Optional[bool] = None,
        with_setuptools: Optional[bool] = None,
    ) -> virtualenv.run.session.Session:
        flags = flags or {}

        flags["no-pip"] = (
            not with_pip if with_pip is not None else flags.pop("no-pip", True)
        )

        flags["no-setuptools"] = (
            not with_setuptools
            if with_setuptools is not None
            else flags.pop("no-setuptools", True)
        )

        # we want wheels to be enabled when pip is required and it has not been explicitly disabled
        flags["no-wheel"] = (
            not with_wheel
            if with_wheel is not None
            else flags.pop("no-wheel", flags["no-pip"])
        )

        if isinstance(executable, Path):
            executable = executable.resolve().as_posix()

        args = [
            "--no-download",
            "--no-periodic-update",
            "--python",
            executable or sys.executable,
        ]

        for flag, value in flags.items():
            if value is True:
                args.append(f"--{flag}")

        args.append(str(path))

        return virtualenv.cli_run(args)

    @classmethod
    def remove_venv(cls, path: Union[Path, str]) -> None:
        if isinstance(path, str):
            path = Path(path)
        assert path.is_dir()
        try:
            shutil.rmtree(str(path))
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
                shutil.rmtree(str(file_path))

    @classmethod
    def get_system_env(cls, naive: bool = False) -> Union["SystemEnv", "GenericEnv"]:
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
        if not naive:
            try:
                Path(__file__).relative_to(prefix)
            except ValueError:
                pass
            else:
                return GenericEnv(base_prefix)

        return SystemEnv(prefix)

    @classmethod
    def get_base_prefix(cls) -> Path:
        if hasattr(sys, "real_prefix"):
            return Path(sys.real_prefix)

        if hasattr(sys, "base_prefix"):
            return Path(sys.base_prefix)

        return Path(sys.prefix)

    @classmethod
    def generate_env_name(cls, name: str, cwd: str) -> str:
        name = name.lower()
        sanitized_name = re.sub(r'[ $`!*@"\\\r\n\t]', "_", name)[:42]
        h = hashlib.sha256(encode(cwd)).digest()
        h = base64.urlsafe_b64encode(h).decode()[:8]

        return f"{sanitized_name}-{h}"


class Env:
    """
    An abstract Python environment.
    """

    def __init__(self, path: Path, base: Optional[Path] = None) -> None:
        self._is_windows = sys.platform == "win32"
        self._is_mingw = sysconfig.get_platform() == "mingw"

        if not self._is_windows or self._is_mingw:
            bin_dir = "bin"
        else:
            bin_dir = "Scripts"
        self._path = path
        self._bin_dir = self._path / bin_dir

        self._base = base or path

        self._marker_env = None
        self._pip_version = None
        self._site_packages = None
        self._paths = None
        self._supported_tags = None
        self._purelib = None
        self._platlib = None
        self._script_dirs = None

        self._embedded_pip_path = None

    @property
    def path(self) -> Path:
        return self._path

    @property
    def base(self) -> Path:
        return self._base

    @property
    def version_info(self) -> Tuple[int]:
        return tuple(self.marker_env["version_info"])

    @property
    def python_implementation(self) -> str:
        return self.marker_env["platform_python_implementation"]

    @property
    def python(self) -> str:
        """
        Path to current python executable
        """
        return self._bin("python")

    @property
    def marker_env(self) -> Dict[str, Any]:
        if self._marker_env is None:
            self._marker_env = self.get_marker_env()

        return self._marker_env

    def get_embedded_wheel(self, distribution):
        return get_embed_wheel(
            distribution, "{}.{}".format(self.version_info[0], self.version_info[1])
        ).path

    @property
    def pip_embedded(self) -> str:
        if self._embedded_pip_path is None:
            self._embedded_pip_path = str(self.get_embedded_wheel("pip") / "pip")
        return self._embedded_pip_path

    @property
    def pip(self) -> str:
        """
        Path to current pip executable
        """
        # we do not use as_posix() here due to issues with windows pathlib2 implementation
        path = self._bin("pip")
        if not Path(path).exists():
            return str(self.pip_embedded)
        return path

    @property
    def platform(self) -> str:
        return sys.platform

    @property
    def os(self) -> str:
        return os.name

    @property
    def pip_version(self) -> Version:
        if self._pip_version is None:
            self._pip_version = self.get_pip_version()

        return self._pip_version

    @property
    def site_packages(self) -> SitePackages:
        if self._site_packages is None:
            # we disable write checks if no user site exist
            fallbacks = [self.usersite] if self.usersite else []
            self._site_packages = SitePackages(
                self.purelib,
                self.platlib,
                fallbacks,
                skip_write_checks=False if fallbacks else True,
            )
        return self._site_packages

    @property
    def usersite(self) -> Optional[Path]:
        if "usersite" in self.paths:
            return Path(self.paths["usersite"])

    @property
    def userbase(self) -> Optional[Path]:
        if "userbase" in self.paths:
            return Path(self.paths["userbase"])

    @property
    def purelib(self) -> Path:
        if self._purelib is None:
            self._purelib = Path(self.paths["purelib"])

        return self._purelib

    @property
    def platlib(self) -> Path:
        if self._platlib is None:
            if "platlib" in self.paths:
                self._platlib = Path(self.paths["platlib"])
            else:
                self._platlib = self.purelib

        return self._platlib

    def is_path_relative_to_lib(self, path: Path) -> bool:
        for lib_path in [self.purelib, self.platlib]:
            try:
                path.relative_to(lib_path)
                return True
            except ValueError:
                pass

        return False

    @property
    def sys_path(self) -> List[str]:
        raise NotImplementedError()

    @property
    def paths(self) -> Dict[str, str]:
        if self._paths is None:
            self._paths = self.get_paths()

        return self._paths

    @property
    def supported_tags(self) -> List[Tag]:
        if self._supported_tags is None:
            self._supported_tags = self.get_supported_tags()

        return self._supported_tags

    @classmethod
    def get_base_prefix(cls) -> Path:
        if hasattr(sys, "real_prefix"):
            return Path(sys.real_prefix)

        if hasattr(sys, "base_prefix"):
            return Path(sys.base_prefix)

        return Path(sys.prefix)

    def get_version_info(self) -> Tuple[int]:
        raise NotImplementedError()

    def get_python_implementation(self) -> str:
        raise NotImplementedError()

    def get_marker_env(self) -> Dict[str, Any]:
        raise NotImplementedError()

    def get_pip_command(self, embedded: bool = False) -> List[str]:
        raise NotImplementedError()

    def get_supported_tags(self) -> List[Tag]:
        raise NotImplementedError()

    def get_pip_version(self) -> Version:
        raise NotImplementedError()

    def get_paths(self) -> Dict[str, str]:
        raise NotImplementedError()

    def is_valid_for_marker(self, marker: BaseMarker) -> bool:
        return marker.validate(self.marker_env)

    def is_sane(self) -> bool:
        """
        Checks whether the current environment is sane or not.
        """
        return True

    def get_command_from_bin(self, bin: str) -> List[str]:
        if bin == "pip":
            # when pip is required we need to ensure that we fallback to
            # embedded pip when pip is not available in the environment
            return self.get_pip_command()

        return [self._bin(bin)]

    def run(self, bin: str, *args: str, **kwargs: Any) -> Union[str, int]:
        cmd = self.get_command_from_bin(bin) + list(args)
        return self._run(cmd, **kwargs)

    def run_pip(self, *args: str, **kwargs: Any) -> Union[int, str]:
        pip = self.get_pip_command(embedded=True)
        cmd = pip + list(args)
        return self._run(cmd, **kwargs)

    def run_python_script(self, content: str, **kwargs: Any) -> str:
        return self.run("python", "-W", "ignore", "-", input_=content, **kwargs)

    def _run(self, cmd: List[str], **kwargs: Any) -> Union[int, str]:
        """
        Run a command inside the Python environment.
        """
        call = kwargs.pop("call", False)
        input_ = kwargs.pop("input_", None)
        env = kwargs.pop("env", {k: v for k, v in os.environ.items()})

        try:
            if self._is_windows:
                kwargs["shell"] = True

            if kwargs.get("shell", False):
                cmd = list_to_shell_command(cmd)

            if input_:
                output = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    input=encode(input_),
                    check=True,
                    **kwargs,
                ).stdout
            elif call:
                return subprocess.call(cmd, stderr=subprocess.STDOUT, env=env, **kwargs)
            else:
                output = subprocess.check_output(
                    cmd, stderr=subprocess.STDOUT, env=env, **kwargs
                )
        except CalledProcessError as e:
            raise EnvCommandError(e, input=input_)

        return decode(output)

    def execute(self, bin: str, *args: str, **kwargs: Any) -> Optional[int]:
        command = self.get_command_from_bin(bin) + list(args)
        env = kwargs.pop("env", {k: v for k, v in os.environ.items()})

        if not self._is_windows:
            return os.execvpe(command[0], command, env=env)
        else:
            exe = subprocess.Popen([command[0]] + command[1:], env=env, **kwargs)
            exe.communicate()
            return exe.returncode

    def is_venv(self) -> bool:
        raise NotImplementedError()

    @property
    def script_dirs(self) -> List[Path]:
        if self._script_dirs is None:
            self._script_dirs = (
                [Path(self.paths["scripts"])]
                if "scripts" in self.paths
                else self._bin_dir
            )
            if self.userbase:
                self._script_dirs.append(self.userbase / self._script_dirs[0].name)
        return self._script_dirs

    def _bin(self, bin: str) -> str:
        """
        Return path to the given executable.
        """
        bin_path = (self._bin_dir / bin).with_suffix(".exe" if self._is_windows else "")
        if not bin_path.exists():
            # On Windows, some executables can be in the base path
            # This is especially true when installing Python with
            # the official installer, where python.exe will be at
            # the root of the env path.
            # This is an edge case and should not be encountered
            # in normal uses but this happens in the sonnet script
            # that creates a fake virtual environment pointing to
            # a base Python install.
            if self._is_windows:
                bin_path = (self._path / bin).with_suffix(".exe")
                if bin_path.exists():
                    return str(bin_path)

            return bin

        return str(bin_path)

    def __eq__(self, other: "Env") -> bool:
        return other.__class__ == self.__class__ and other.path == self.path

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}("{self._path}")'


class SystemEnv(Env):
    """
    A system (i.e. not a virtualenv) Python environment.
    """

    @property
    def python(self) -> str:
        return sys.executable

    @property
    def sys_path(self) -> List[str]:
        return sys.path

    def get_version_info(self) -> Tuple[int]:
        return sys.version_info

    def get_python_implementation(self) -> str:
        return platform.python_implementation()

    def get_pip_command(self, embedded: bool = False) -> List[str]:
        # If we're not in a venv, assume the interpreter we're running on
        # has a pip and use that
        return [sys.executable, self.pip_embedded if embedded else self.pip]

    def get_paths(self) -> Dict[str, str]:
        # We can't use sysconfig.get_paths() because
        # on some distributions it does not return the proper paths
        # (those used by pip for instance). We go through distutils
        # to get the proper ones.
        import site

        from distutils.command.install import SCHEME_KEYS  # noqa
        from distutils.core import Distribution

        d = Distribution()
        d.parse_config_files()
        obj = d.get_command_obj("install", create=True)
        obj.finalize_options()

        paths = sysconfig.get_paths().copy()
        for key in SCHEME_KEYS:
            if key == "headers":
                # headers is not a path returned by sysconfig.get_paths()
                continue

            paths[key] = getattr(obj, f"install_{key}")

        if site.check_enableusersite() and hasattr(obj, "install_usersite"):
            paths["usersite"] = getattr(obj, "install_usersite")
            paths["userbase"] = getattr(obj, "install_userbase")

        return paths

    def get_supported_tags(self) -> List[Tag]:
        return list(sys_tags())

    def get_marker_env(self) -> Dict[str, Any]:
        if hasattr(sys, "implementation"):
            info = sys.implementation.version
            iver = "{0.major}.{0.minor}.{0.micro}".format(info)
            kind = info.releaselevel
            if kind != "final":
                iver += kind[0] + str(info.serial)

            implementation_name = sys.implementation.name
        else:
            iver = "0"
            implementation_name = ""

        return {
            "implementation_name": implementation_name,
            "implementation_version": iver,
            "os_name": os.name,
            "platform_machine": platform.machine(),
            "platform_release": platform.release(),
            "platform_system": platform.system(),
            "platform_version": platform.version(),
            "python_full_version": platform.python_version(),
            "platform_python_implementation": platform.python_implementation(),
            "python_version": ".".join(
                v for v in platform.python_version().split(".")[:2]
            ),
            "sys_platform": sys.platform,
            "version_info": sys.version_info,
            # Extra information
            "interpreter_name": interpreter_name(),
            "interpreter_version": interpreter_version(),
        }

    def get_pip_version(self) -> Version:
        from pip import __version__

        return Version.parse(__version__)

    def is_venv(self) -> bool:
        return self._path != self._base


class VirtualEnv(Env):
    """
    A virtual Python environment.
    """

    def __init__(self, path: Path, base: Optional[Path] = None) -> None:
        super().__init__(path, base)

        # If base is None, it probably means this is
        # a virtualenv created from VIRTUAL_ENV.
        # In this case we need to get sys.base_prefix
        # from inside the virtualenv.
        if base is None:
            self._base = Path(self.run_python_script(GET_BASE_PREFIX).strip())

    @property
    def sys_path(self) -> List[str]:
        output = self.run_python_script(GET_SYS_PATH)
        return json.loads(output)

    def get_version_info(self) -> Tuple[int]:
        output = self.run_python_script(GET_PYTHON_VERSION)

        return tuple([int(s) for s in output.strip().split(".")])

    def get_python_implementation(self) -> str:
        return self.marker_env["platform_python_implementation"]

    def get_pip_command(self, embedded: bool = False) -> List[str]:
        # We're in a virtualenv that is known to be sane,
        # so assume that we have a functional pip
        return [self._bin("python"), self.pip_embedded if embedded else self.pip]

    def get_supported_tags(self) -> List[Tag]:
        file_path = Path(packaging.tags.__file__)
        if file_path.suffix == ".pyc":
            # Python 2
            file_path = file_path.with_suffix(".py")

        with file_path.open(encoding="utf-8") as f:
            script = decode(f.read())

        script = script.replace(
            "from ._typing import TYPE_CHECKING, cast",
            "TYPE_CHECKING = False\ncast = lambda type_, value: value",
        )
        script = script.replace(
            "from ._typing import MYPY_CHECK_RUNNING, cast",
            "MYPY_CHECK_RUNNING = False\ncast = lambda type_, value: value",
        )

        script += textwrap.dedent(
            """
            import json

            print(json.dumps([(t.interpreter, t.abi, t.platform) for t in sys_tags()]))
            """
        )

        output = self.run_python_script(script)

        return [Tag(*t) for t in json.loads(output)]

    def get_marker_env(self) -> Dict[str, Any]:
        output = self.run_python_script(GET_ENVIRONMENT_INFO)

        return json.loads(output)

    def get_pip_version(self) -> Version:
        output = self.run_pip("--version").strip()
        m = re.match("pip (.+?)(?: from .+)?$", output)
        if not m:
            return Version.parse("0.0")

        return Version.parse(m.group(1))

    def get_paths(self) -> Dict[str, str]:
        output = self.run_python_script(GET_PATHS)
        return json.loads(output)

    def is_venv(self) -> bool:
        return True

    def is_sane(self) -> bool:
        # A virtualenv is considered sane if "python" exists.
        return os.path.exists(self.python)

    def _run(self, cmd: List[str], **kwargs: Any) -> Optional[int]:
        kwargs["env"] = self.get_temp_environ(environ=kwargs.get("env"))
        return super()._run(cmd, **kwargs)

    def get_temp_environ(
        self,
        environ: Optional[Dict[str, str]] = None,
        exclude: Optional[List[str]] = None,
        **kwargs: str,
    ) -> Dict[str, str]:
        exclude = exclude or []
        exclude.extend(["PYTHONHOME", "__PYVENV_LAUNCHER__"])

        if environ:
            environ = deepcopy(environ)
            for key in exclude:
                environ.pop(key, None)
        else:
            environ = {k: v for k, v in os.environ.items() if k not in exclude}

        environ.update(kwargs)

        environ["PATH"] = self._updated_path()
        environ["VIRTUAL_ENV"] = str(self._path)

        return environ

    def execute(self, bin: str, *args: str, **kwargs: Any) -> Optional[int]:
        kwargs["env"] = self.get_temp_environ(environ=kwargs.get("env"))
        return super().execute(bin, *args, **kwargs)

    @contextmanager
    def temp_environ(self) -> Iterator[None]:
        environ = dict(os.environ)
        try:
            yield
        finally:
            os.environ.clear()
            os.environ.update(environ)

    def _updated_path(self) -> str:
        return os.pathsep.join([str(self._bin_dir), os.environ.get("PATH", "")])


class GenericEnv(VirtualEnv):
    def is_venv(self) -> bool:
        return self._path != self._base


class NullEnv(SystemEnv):
    def __init__(
        self, path: Path = None, base: Optional[Path] = None, execute: bool = False
    ) -> None:
        if path is None:
            path = Path(sys.prefix)

        super().__init__(path, base=base)

        self._execute = execute
        self.executed = []

    def get_pip_command(self, embedded: bool = False) -> List[str]:
        return [self._bin("python"), self.pip_embedded if embedded else self.pip]

    def _run(self, cmd: List[str], **kwargs: Any) -> int:
        self.executed.append(cmd)

        if self._execute:
            return super()._run(cmd, **kwargs)

    def execute(self, bin: str, *args: str, **kwargs: Any) -> Optional[int]:
        self.executed.append([bin] + list(args))

        if self._execute:
            return super().execute(bin, *args, **kwargs)

    def _bin(self, bin: str) -> str:
        return bin


@contextmanager
def ephemeral_environment(
    executable=None,
    flags: Dict[str, bool] = None,
    with_pip: bool = False,
    with_wheel: Optional[bool] = None,
    with_setuptools: Optional[bool] = None,
) -> ContextManager[VirtualEnv]:
    with temporary_directory() as tmp_dir:
        # TODO: cache PEP 517 build environment corresponding to each project venv
        venv_dir = Path(tmp_dir) / ".venv"
        EnvManager.build_venv(
            path=venv_dir.as_posix(),
            executable=executable,
            flags=flags,
            with_pip=with_pip,
            with_wheel=with_wheel,
            with_setuptools=with_setuptools,
        )
        yield VirtualEnv(venv_dir, venv_dir)


class MockEnv(NullEnv):
    def __init__(
        self,
        version_info: Tuple[int, int, int] = (3, 7, 0),
        python_implementation: str = "CPython",
        platform: str = "darwin",
        os_name: str = "posix",
        is_venv: bool = False,
        pip_version: str = "19.1",
        sys_path: Optional[List[str]] = None,
        marker_env: Dict[str, Any] = None,
        supported_tags: List[Tag] = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)

        self._version_info = version_info
        self._python_implementation = python_implementation
        self._platform = platform
        self._os_name = os_name
        self._is_venv = is_venv
        self._pip_version = Version.parse(pip_version)
        self._sys_path = sys_path
        self._mock_marker_env = marker_env
        self._supported_tags = supported_tags

    @property
    def platform(self) -> str:
        return self._platform

    @property
    def os(self) -> str:
        return self._os_name

    @property
    def pip_version(self) -> Version:
        return self._pip_version

    @property
    def sys_path(self) -> List[str]:
        if self._sys_path is None:
            return super().sys_path

        return self._sys_path

    def get_marker_env(self) -> Dict[str, Any]:
        if self._mock_marker_env is not None:
            return self._mock_marker_env

        marker_env = super().get_marker_env()
        marker_env["python_implementation"] = self._python_implementation
        marker_env["version_info"] = self._version_info
        marker_env["python_version"] = ".".join(str(v) for v in self._version_info[:2])
        marker_env["python_full_version"] = ".".join(str(v) for v in self._version_info)
        marker_env["sys_platform"] = self._platform
        marker_env["interpreter_name"] = self._python_implementation.lower()
        marker_env["interpreter_version"] = "cp" + "".join(
            str(v) for v in self._version_info[:2]
        )

        return marker_env

    def is_venv(self) -> bool:
        return self._is_venv
