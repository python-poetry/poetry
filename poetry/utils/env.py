import base64
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import sysconfig
import warnings

import tomlkit

from contextlib import contextmanager
from subprocess import CalledProcessError
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from clikit.api.io import IO

from poetry.config import Config
from poetry.locations import CACHE_DIR
from poetry.semver import Version
from poetry.utils._compat import Path
from poetry.utils._compat import decode
from poetry.utils._compat import encode
from poetry.utils._compat import list_to_shell_command
from poetry.utils.toml_file import TomlFile
from poetry.version.markers import BaseMarker


GET_ENVIRONMENT_INFO = """\
import json
import os
import platform
import sys

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
    "python_version": platform.python_version()[:3],
    "sys_platform": sys.platform,
    "version_info": tuple(sys.version_info),
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

GET_CONFIG_VAR = """\
import sysconfig

print(sysconfig.get_config_var("{config_var}")),
"""

GET_PYTHON_VERSION = """\
import sys

print('.'.join([str(s) for s in sys.version_info[:3]]))
"""

CREATE_VENV_COMMAND = """\
path = {!r}

try:
    from venv import EnvBuilder

    builder = EnvBuilder(with_pip=True)
    build = builder.create
except ImportError:
    # We fallback on virtualenv for Python 2.7
    from virtualenv import create_environment

    build = create_environment

build(path)"""


class EnvError(Exception):

    pass


class EnvCommandError(EnvError):
    def __init__(self, e):  # type: (CalledProcessError) -> None
        message = "Command {} errored with the following output: \n{}".format(
            e.cmd, decode(e.output)
        )

        super(EnvCommandError, self).__init__(message)


class EnvManager(object):
    """
    Environments manager
    """

    _env = None

    ENVS_FILE = "envs.toml"

    def __init__(self, config=None):  # type: (Config) -> None
        if config is None:
            config = Config.create("config.toml")

        self._config = config

    def activate(self, python, cwd, io):  # type: (str, Optional[Path], IO) -> Env
        venv_path = self._config.setting("settings.virtualenvs.path")
        if venv_path is None:
            venv_path = Path(CACHE_DIR) / "virtualenvs"
        else:
            venv_path = Path(venv_path)

        envs_file = TomlFile(venv_path / self.ENVS_FILE)

        try:
            python_version = Version.parse(python)
            python = "python{}".format(python_version.major)
            if python_version.precision > 1:
                python += ".{}".format(python_version.minor)
        except ValueError:
            # Executable in PATH or full executable path
            pass

        try:
            python_version = decode(
                subprocess.check_output(
                    " ".join(
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
        minor = "{}.{}".format(python_version.major, python_version.minor)
        patch = python_version.text

        create = False
        envs = tomlkit.document()
        base_env_name = self.generate_env_name(cwd.name, str(cwd))
        if envs_file.exists():
            envs = envs_file.read()
            current_env = envs.get(base_env_name)
            if current_env is not None:
                current_minor = current_env["minor"]
                current_patch = current_env["patch"]

                if current_minor == minor and current_patch != patch:
                    # We need to recreate
                    create = True

        name = "{}-py{}".format(base_env_name, minor)
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

            self.create_venv(cwd, io, executable=python, force=create)

        # Activate
        envs[base_env_name] = {"minor": minor, "patch": patch}
        envs_file.write(envs)

        return self.get(cwd, reload=True)

    def deactivate(self, cwd, io):  # type: (Optional[Path], IO) -> None
        venv_path = self._config.setting("settings.virtualenvs.path")
        if venv_path is None:
            venv_path = Path(CACHE_DIR) / "virtualenvs"
        else:
            venv_path = Path(venv_path)

        name = cwd.name
        name = self.generate_env_name(name, str(cwd))

        envs_file = TomlFile(venv_path / self.ENVS_FILE)
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

    def get(self, cwd, reload=False):  # type: (Path, bool) -> Env
        if self._env is not None and not reload:
            return self._env

        python_minor = ".".join([str(v) for v in sys.version_info[:2]])

        venv_path = self._config.setting("settings.virtualenvs.path")
        if venv_path is None:
            venv_path = Path(CACHE_DIR) / "virtualenvs"
        else:
            venv_path = Path(venv_path)

        envs_file = TomlFile(venv_path / self.ENVS_FILE)
        env = None
        base_env_name = self.generate_env_name(cwd.name, str(cwd))
        if envs_file.exists():
            envs = envs_file.read()
            env = envs.get(base_env_name)
            if env:
                python_minor = env["minor"]

        # Check if we are inside a virtualenv or not
        in_venv = os.environ.get("VIRTUAL_ENV") is not None

        if not in_venv or env is not None:
            # Checking if a local virtualenv exists
            if (cwd / ".venv").exists():
                venv = cwd / ".venv"

                return VirtualEnv(venv)

            create_venv = self._config.setting("settings.virtualenvs.create", True)

            if not create_venv:
                return SystemEnv(Path(sys.prefix))

            venv_path = self._config.setting("settings.virtualenvs.path")
            if venv_path is None:
                venv_path = Path(CACHE_DIR) / "virtualenvs"
            else:
                venv_path = Path(venv_path)

            name = "{}-py{}".format(base_env_name, python_minor.strip())

            venv = venv_path / name

            if not venv.exists():
                return SystemEnv(Path(sys.prefix))

            return VirtualEnv(venv)

        if os.environ.get("VIRTUAL_ENV") is not None:
            prefix = Path(os.environ["VIRTUAL_ENV"])
            base_prefix = None
        else:
            prefix = Path(sys.prefix)
            base_prefix = self.get_base_prefix()

        return VirtualEnv(prefix, base_prefix)

    def list(self, cwd, name=None):  # type: (Path, Optional[str]) -> List[VirtualEnv]
        if name is None:
            name = cwd.name

        venv_name = self.generate_env_name(name, str(cwd))

        venv_path = self._config.setting("settings.virtualenvs.path")
        if venv_path is None:
            venv_path = Path(CACHE_DIR) / "virtualenvs"
        else:
            venv_path = Path(venv_path)

        return [
            VirtualEnv(Path(p))
            for p in sorted(venv_path.glob("{}-py*".format(venv_name)))
        ]

    def remove(self, python, cwd):  # type: (str, Optional[Path]) -> Env
        venv_path = self._config.setting("settings.virtualenvs.path")
        if venv_path is None:
            venv_path = Path(CACHE_DIR) / "virtualenvs"
        else:
            venv_path = Path(venv_path)

        envs_file = TomlFile(venv_path / self.ENVS_FILE)
        base_env_name = self.generate_env_name(cwd.name, str(cwd))

        if python.startswith(base_env_name):
            venvs = self.list(cwd)
            for venv in venvs:
                if venv.path.name == python:
                    # Exact virtualenv name
                    if not envs_file.exists():
                        self.remove_venv(str(venv.path))

                        return venv

                    venv_minor = ".".join(str(v) for v in venv.version_info[:2])
                    base_env_name = self.generate_env_name(cwd.name, str(cwd))
                    envs = envs_file.read()

                    current_env = envs.get(base_env_name)
                    if not current_env:
                        self.remove_venv(str(venv.path))

                        return venv

                    if current_env["minor"] == venv_minor:
                        del envs[base_env_name]
                        envs_file.write(envs)

                    self.remove_venv(str(venv.path))

                    return venv

            raise ValueError(
                '<warning>Environment "{}" does not exist.</warning>'.format(python)
            )

        try:
            python_version = Version.parse(python)
            python = "python{}".format(python_version.major)
            if python_version.precision > 1:
                python += ".{}".format(python_version.minor)
        except ValueError:
            # Executable in PATH or full executable path
            pass

        try:
            python_version = decode(
                subprocess.check_output(
                    " ".join(
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
        minor = "{}.{}".format(python_version.major, python_version.minor)

        name = "{}-py{}".format(base_env_name, minor)
        venv = venv_path / name

        if not venv.exists():
            raise ValueError(
                '<warning>Environment "{}" does not exist.</warning>'.format(name)
            )

        if envs_file.exists():
            envs = envs_file.read()
            current_env = envs.get(base_env_name)
            if current_env is not None:
                current_minor = current_env["minor"]

                if current_minor == minor:
                    del envs[base_env_name]
                    envs_file.write(envs)

        self.remove_venv(str(venv))

        return VirtualEnv(venv)

    def create_venv(
        self, cwd, io, name=None, executable=None, force=False
    ):  # type: (Path, IO, Optional[str], Optional[str], bool) -> Env
        if self._env is not None and not force:
            return self._env

        env = self.get(cwd, reload=True)
        if env.is_venv() and not force:
            # Already inside a virtualenv.
            return env

        create_venv = self._config.setting("settings.virtualenvs.create")
        root_venv = self._config.setting("settings.virtualenvs.in-project")

        venv_path = self._config.setting("settings.virtualenvs.path")
        if root_venv:
            venv_path = cwd / ".venv"
        elif venv_path is None:
            venv_path = Path(CACHE_DIR) / "virtualenvs"
        else:
            venv_path = Path(venv_path)

        if not name:
            name = cwd.name

        python_minor = ".".join([str(v) for v in sys.version_info[:2]])
        if executable:
            python_minor = decode(
                subprocess.check_output(
                    " ".join(
                        [
                            executable,
                            "-c",
                            "\"import sys; print('.'.join([str(s) for s in sys.version_info[:2]]))\"",
                        ]
                    ),
                    shell=True,
                )
            )

        if root_venv:
            venv = venv_path
        else:
            name = self.generate_env_name(name, str(cwd))
            name = "{}-py{}".format(name, python_minor.strip())
            venv = venv_path / name

        if not venv.exists():
            if create_venv is False:
                io.write_line(
                    "<fg=black;bg=yellow>"
                    "Skipping virtualenv creation, "
                    "as specified in config file."
                    "</>"
                )

                return SystemEnv(Path(sys.prefix))

            io.write_line(
                "Creating virtualenv <info>{}</> in {}".format(name, str(venv_path))
            )

            self.build_venv(str(venv), executable=executable)
        else:
            if force:
                io.write_line(
                    "Recreating virtualenv <info>{}</> in {}".format(name, str(venv))
                )
                self.remove_venv(str(venv))
                self.build_venv(str(venv), executable=executable)
            elif io.is_very_verbose():
                io.write_line("Virtualenv <info>{}</> already exists.".format(name))

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
            return SystemEnv(Path(sys.prefix), self.get_base_prefix())

        return VirtualEnv(venv)

    def build_venv(self, path, executable=None):
        if executable is not None:
            # Create virtualenv by using an external executable
            try:
                p = subprocess.Popen(
                    " ".join([executable, "-"]), stdin=subprocess.PIPE, shell=True
                )
                p.communicate(encode(CREATE_VENV_COMMAND.format(path)))
            except CalledProcessError as e:
                raise EnvCommandError(e)

            return

        try:
            from venv import EnvBuilder

            builder = EnvBuilder(with_pip=True)
            build = builder.create
        except ImportError:
            # We fallback on virtualenv for Python 2.7
            from virtualenv import create_environment

            build = create_environment

        build(path)

    def remove_venv(self, path):  # type: (str) -> None
        shutil.rmtree(path)

    def get_base_prefix(self):  # type: () -> Path
        if hasattr(sys, "real_prefix"):
            return sys.real_prefix

        if hasattr(sys, "base_prefix"):
            return sys.base_prefix

        return sys.prefix

    @classmethod
    def generate_env_name(cls, name, cwd):  # type: (str, str) -> str
        name = name.lower()
        sanitized_name = re.sub(r'[ $`!*@"\\\r\n\t]', "_", name)[:42]
        h = hashlib.sha256(encode(cwd)).digest()
        h = base64.urlsafe_b64encode(h).decode()[:8]

        return "{}-{}".format(sanitized_name, h)


class Env(object):
    """
    An abstract Python environment.
    """

    def __init__(self, path, base=None):  # type: (Path, Optional[Path]) -> None
        self._is_windows = sys.platform == "win32"

        self._path = path
        bin_dir = "bin" if not self._is_windows else "Scripts"
        self._bin_dir = self._path / bin_dir

        self._base = base or path

        self._marker_env = None

    @property
    def path(self):  # type: () -> Path
        return self._path

    @property
    def base(self):  # type: () -> Path
        return self._base

    @property
    def version_info(self):  # type: () -> Tuple[int]
        return tuple(self.marker_env["version_info"])

    @property
    def python_implementation(self):  # type: () -> str
        return self.marker_env["platform_python_implementation"]

    @property
    def python(self):  # type: () -> str
        """
        Path to current python executable
        """
        return self._bin("python")

    @property
    def marker_env(self):
        if self._marker_env is None:
            self._marker_env = self.get_marker_env()

        return self._marker_env

    @property
    def pip(self):  # type: () -> str
        """
        Path to current pip executable
        """
        return self._bin("pip")

    @property
    def platform(self):  # type: () -> str
        return sys.platform

    @property
    def os(self):  # type: () -> str
        return os.name

    @classmethod
    def get_base_prefix(cls):  # type: () -> Path
        if hasattr(sys, "real_prefix"):
            return sys.real_prefix

        if hasattr(sys, "base_prefix"):
            return sys.base_prefix

        return sys.prefix

    def get_version_info(self):  # type: () -> Tuple[int]
        raise NotImplementedError()

    def get_python_implementation(self):  # type: () -> str
        raise NotImplementedError()

    def get_marker_env(self):  # type: () -> Dict[str, Any]
        raise NotImplementedError()

    def config_var(self, var):  # type: (str) -> Any
        raise NotImplementedError()

    def is_valid_for_marker(self, marker):  # type: (BaseMarker) -> bool
        return marker.validate(self.marker_env)

    def is_sane(self):  # type: () -> bool
        """
        Checks whether the current environment is sane or not.
        """
        return True

    def run(self, bin, *args, **kwargs):
        """
        Run a command inside the Python environment.
        """
        bin = self._bin(bin)

        cmd = [bin] + list(args)
        shell = kwargs.get("shell", False)
        call = kwargs.pop("call", False)
        input_ = kwargs.pop("input_", None)

        if shell:
            cmd = list_to_shell_command(cmd)

        try:
            if self._is_windows:
                kwargs["shell"] = True

            if input_:
                p = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    **kwargs
                )
                output = p.communicate(encode(input_))[0]
            elif call:
                return subprocess.call(cmd, stderr=subprocess.STDOUT, **kwargs)
            else:
                output = subprocess.check_output(
                    cmd, stderr=subprocess.STDOUT, **kwargs
                )
        except CalledProcessError as e:
            raise EnvCommandError(e)

        return decode(output)

    def execute(self, bin, *args, **kwargs):
        bin = self._bin(bin)

        return subprocess.call([bin] + list(args), **kwargs)

    def is_venv(self):  # type: () -> bool
        raise NotImplementedError()

    def _bin(self, bin):  # type: (str) -> str
        """
        Return path to the given executable.
        """
        bin_path = (self._bin_dir / bin).with_suffix(".exe" if self._is_windows else "")
        if not bin_path.exists():
            return bin

        return str(bin_path)

    def __eq__(self, other):  # type: (Env) -> bool
        return other.__class__ == self.__class__ and other.path == self.path

    def __repr__(self):
        return '{}("{}")'.format(self.__class__.__name__, self._path)


class SystemEnv(Env):
    """
    A system (i.e. not a virtualenv) Python environment.
    """

    def get_version_info(self):  # type: () -> Tuple[int]
        return sys.version_info

    def get_python_implementation(self):  # type: () -> str
        return platform.python_implementation()

    def get_marker_env(self):  # type: () -> Dict[str, Any]
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
            "python_version": platform.python_version()[:3],
            "sys_platform": sys.platform,
            "version_info": sys.version_info,
        }

    def config_var(self, var):  # type: (str) -> Any
        try:
            return sysconfig.get_config_var(var)
        except IOError as e:
            warnings.warn("{0}".format(e), RuntimeWarning)

            return

    def is_venv(self):  # type: () -> bool
        return self._path != self._base


class VirtualEnv(Env):
    """
    A virtual Python environment.
    """

    def __init__(self, path, base=None):  # type: (Path, Optional[Path]) -> None
        super(VirtualEnv, self).__init__(path, base)

        # If base is None, it probably means this is
        # a virtualenv created from VIRTUAL_ENV.
        # In this case we need to get sys.base_prefix
        # from inside the virtualenv.
        if base is None:
            self._base = Path(self.run("python", "-", input_=GET_BASE_PREFIX).strip())

    def get_version_info(self):  # type: () -> Tuple[int]
        output = self.run("python", "-", input_=GET_PYTHON_VERSION)

        return tuple([int(s) for s in output.strip().split(".")])

    def get_python_implementation(self):  # type: () -> str
        return self.marker_env["platform_python_implementation"]

    def get_marker_env(self):  # type: () -> Dict[str, Any]
        output = self.run("python", "-", input_=GET_ENVIRONMENT_INFO)

        return json.loads(output)

    def config_var(self, var):  # type: (str) -> Any
        try:
            value = self.run(
                "python", "-", input_=GET_CONFIG_VAR.format(config_var=var)
            ).strip()
        except EnvCommandError as e:
            warnings.warn("{0}".format(e), RuntimeWarning)
            return None

        if value == "None":
            value = None
        elif value == "1":
            value = 1
        elif value == "0":
            value = 0

        return value

    def is_venv(self):  # type: () -> bool
        return True

    def is_sane(self):
        # A virtualenv is considered sane if both "python" and "pip" exist.
        return os.path.exists(self._bin("python")) and os.path.exists(self._bin("pip"))

    def run(self, bin, *args, **kwargs):
        with self.temp_environ():
            os.environ["PATH"] = self._updated_path()
            os.environ["VIRTUAL_ENV"] = str(self._path)

            self.unset_env("PYTHONHOME")
            self.unset_env("__PYVENV_LAUNCHER__")

            return super(VirtualEnv, self).run(bin, *args, **kwargs)

    def execute(self, bin, *args, **kwargs):
        with self.temp_environ():
            os.environ["PATH"] = self._updated_path()
            os.environ["VIRTUAL_ENV"] = str(self._path)

            self.unset_env("PYTHONHOME")
            self.unset_env("__PYVENV_LAUNCHER__")

            return super(VirtualEnv, self).execute(bin, *args, **kwargs)

    @contextmanager
    def temp_environ(self):
        environ = dict(os.environ)
        try:
            yield
        finally:
            os.environ.clear()
            os.environ.update(environ)

    def unset_env(self, key):
        if key in os.environ:
            del os.environ[key]

    def _updated_path(self):
        return os.pathsep.join([str(self._bin_dir), os.environ["PATH"]])


class NullEnv(SystemEnv):
    def __init__(self, path=None, base=None, execute=False):
        if path is None:
            path = Path(sys.prefix)

        super(NullEnv, self).__init__(path, base=base)

        self._execute = execute
        self.executed = []

    def run(self, bin, *args, **kwargs):
        self.executed.append([bin] + list(args))

        if self._execute:
            return super(NullEnv, self).run(bin, *args, **kwargs)

    def execute(self, bin, *args, **kwargs):
        self.executed.append([bin] + list(args))

        if self._execute:
            return super(NullEnv, self).execute(bin, *args, **kwargs)

    def _bin(self, bin):
        return bin


class MockEnv(NullEnv):
    def __init__(
        self,
        version_info=(3, 7, 0),
        python_implementation="CPython",
        platform="darwin",
        os_name="posix",
        is_venv=False,
        **kwargs
    ):
        super(MockEnv, self).__init__(**kwargs)

        self._version_info = version_info
        self._python_implementation = python_implementation
        self._platform = platform
        self._os_name = os_name
        self._is_venv = is_venv

    @property
    def version_info(self):  # type: () -> Tuple[int]
        return self._version_info

    @property
    def python_implementation(self):  # type: () -> str
        return self._python_implementation

    @property
    def platform(self):  # type: () -> str
        return self._platform

    @property
    def os(self):  # type: () -> str
        return self._os_name

    def is_venv(self):  # type: () -> bool
        return self._is_venv
