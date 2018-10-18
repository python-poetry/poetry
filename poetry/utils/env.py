import json
import os
import platform
import subprocess
import sys
import sysconfig
import warnings

from contextlib import contextmanager
from subprocess import CalledProcessError
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple

from poetry.config import Config
from poetry.locations import CACHE_DIR
from poetry.utils._compat import Path
from poetry.utils._compat import decode
from poetry.version.markers import BaseMarker


class EnvError(Exception):

    pass


class EnvCommandError(EnvError):
    def __init__(self, e):  # type: (CalledProcessError) -> None
        message = "Command {} errored with the following output: \n{}".format(
            e.cmd, decode(e.output)
        )

        super(EnvCommandError, self).__init__(message)


class Env(object):
    """
    An abstract Python environment.
    """

    _env = None

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

    @classmethod
    def get(cls, reload=False, cwd=None):  # type: (IO, bool) -> Env
        if cls._env is not None and not reload:
            return cls._env

        # Check if we are inside a virtualenv or not
        in_venv = (
            os.environ.get("VIRTUAL_ENV") is not None
            or hasattr(sys, "real_prefix")
            or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
        )

        if not in_venv:
            # Checking if a local virtualenv exists
            if cwd and (cwd / ".venv").exists():
                venv = cwd / ".venv"

                return VirtualEnv(Path(venv))

            config = Config.create("config.toml")
            create_venv = config.setting("settings.virtualenvs.create", True)

            if not create_venv:
                return SystemEnv(Path(sys.prefix))

            venv_path = config.setting("settings.virtualenvs.path")
            if venv_path is None:
                venv_path = Path(CACHE_DIR) / "virtualenvs"
            else:
                venv_path = Path(venv_path)

            if cwd is None:
                cwd = Path.cwd()

            name = cwd.name
            name = "{}-py{}".format(
                name, ".".join([str(v) for v in sys.version_info[:2]])
            )

            venv = venv_path / name

            if not venv.exists():
                return SystemEnv(Path(sys.prefix))

            return VirtualEnv(venv)

        if os.environ.get("VIRTUAL_ENV") is not None:
            prefix = Path(os.environ["VIRTUAL_ENV"])
            base_prefix = None
        else:
            prefix = Path(sys.prefix)
            base_prefix = cls.get_base_prefix()

        return VirtualEnv(prefix, base_prefix)

    @classmethod
    def create_venv(cls, io, name=None, cwd=None):  # type: (IO, bool, Path) -> Env
        if cls._env is not None:
            return cls._env

        env = cls.get(cwd=cwd)
        if env.is_venv():
            # Already inside a virtualenv.
            return env

        config = Config.create("config.toml")

        create_venv = config.setting("settings.virtualenvs.create")
        root_venv = config.setting("settings.virtualenvs.in-project")

        venv_path = config.setting("settings.virtualenvs.path")
        if root_venv:
            if not cwd:
                raise RuntimeError("Unable to determine the project's directory")

            venv_path = cwd / ".venv"
        elif venv_path is None:
            venv_path = Path(CACHE_DIR) / "virtualenvs"
        else:
            venv_path = Path(venv_path)

        if not name:
            if not cwd:
                cwd = Path.cwd()

            name = cwd.name

        name = "{}-py{}".format(name, ".".join([str(v) for v in sys.version_info[:2]]))

        if root_venv:
            venv = venv_path
        else:
            venv = venv_path / name

        if not venv.exists():
            if create_venv is False:
                io.writeln(
                    "<fg=black;bg=yellow>"
                    "Skipping virtualenv creation, "
                    "as specified in config file."
                    "</>"
                )

                return SystemEnv(Path(sys.prefix))

            io.writeln(
                "Creating virtualenv <info>{}</> in {}".format(name, str(venv_path))
            )

            cls.build_venv(str(venv))
        else:
            if io.is_very_verbose():
                io.writeln("Virtualenv <info>{}</> already exists.".format(name))

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
            return SystemEnv(Path(sys.prefix), cls.get_base_prefix())

        return VirtualEnv(venv)

    @classmethod
    def build_venv(cls, path):
        try:
            from venv import EnvBuilder

            builder = EnvBuilder(with_pip=True)
            build = builder.create
        except ImportError:
            # We fallback on virtualenv for Python 2.7
            from virtualenv import create_environment

            build = create_environment

        build(path)

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

        if shell:
            cmd = " ".join(cmd)

        try:
            if self._is_windows:
                kwargs["shell"] = True

            if call:
                return subprocess.call(cmd, stderr=subprocess.STDOUT, **kwargs)

            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, **kwargs)
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
            self._base = Path(
                self.run(
                    "python",
                    "-c",
                    '"import sys; '
                    "print("
                    "    getattr("
                    "        sys,"
                    "        'real_prefix', "
                    "        getattr(sys, 'base_prefix', sys.prefix)"
                    "    )"
                    ')"',
                    shell=True,
                ).strip()
            )

    def get_version_info(self):  # type: () -> Tuple[int]
        output = self.run(
            "python",
            "-c",
            "\"import sys; print('.'.join([str(s) for s in sys.version_info[:3]]))\"",
            shell=True,
        )

        return tuple([int(s) for s in output.strip().split(".")])

    def get_python_implementation(self):  # type: () -> str
        return self.marker_env["platform_python_implementation"]

    def get_marker_env(self):  # type: () -> Dict[str, Any]
        output = self.run(
            "python",
            "-c",
            '"import json; import os; import platform; import sys; '
            "implementation = getattr(sys, 'implementation', None); "
            "iver = '{0.major}.{0.minor}.{0.micro}'.format(implementation.version) if implementation else '0'; "
            "implementation_name = implementation.name if implementation else ''; "
            "env = {"
            "'implementation_name': implementation_name,"
            "'implementation_version': iver,"
            "'os_name': os.name,"
            "'platform_machine': platform.machine(),"
            "'platform_release': platform.release(),"
            "'platform_system': platform.system(),"
            "'platform_version': platform.version(),"
            "'python_full_version': platform.python_version(),"
            "'platform_python_implementation': platform.python_implementation(),"
            "'python_version': platform.python_version()[:3],"
            "'sys_platform': sys.platform,"
            "'version_info': sys.version_info[:3],"
            "};"
            'print(json.dumps(env))"',
            shell=True,
        )

        return json.loads(output)

    def config_var(self, var):  # type: (str) -> Any
        try:
            value = self.run(
                "python",
                "-c",
                '"import sysconfig; '
                "print(sysconfig.get_config_var('{}'))\"".format(var),
                shell=True,
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

    def run(self, bin, *args):
        self.executed.append([bin] + list(args))

        if self._execute:
            return super(NullEnv, self).run(bin, *args)

    def _bin(self, bin):
        return bin
