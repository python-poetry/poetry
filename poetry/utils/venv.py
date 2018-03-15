import os
import subprocess
import sys

from contextlib import contextmanager
from pathlib import Path
from subprocess import CalledProcessError

from venv import EnvBuilder

from poetry.config import Config
from poetry.locations import CACHE_DIR


class VenvError(Exception):

    pass


class VenvCommandError(VenvError):

    def __init__(self, e: CalledProcessError):
        message = f'Command {e.cmd} errored with the following output: \n' \
                  f'{e.output.decode()}'

        super().__init__(message)


class Venv:

    def __init__(self, venv=None):
        self._venv = venv
        if self._venv:
            self._venv = Path(self._venv)

        self._bin_dir = None
        if venv:
            bin_dir = 'bin' if sys.platform != 'win32' else 'Scripts'
            self._bin_dir = self._venv / bin_dir

        self._version_info = None

    @classmethod
    def create(cls, io, name=None) -> 'Venv':
        if 'VIRTUAL_ENV' not in os.environ:
            # Not in a virtualenv
            # Checking if we need to create one
            config = Config.create('config.toml')

            create_venv = config.setting('settings.virtualenvs.create')

            venv_path = config.setting('settings.virtualenvs.path')
            if venv_path is None:
                venv_path = Path(CACHE_DIR) / 'virtualenvs'
            else:
                venv_path = Path(venv_path)

            if not name:
                name = Path.cwd().name

            name = f'{name}-py{".".join([str(v) for v in sys.version_info[:2]])}'

            venv = venv_path / name
            if not venv.exists():
                if create_venv is False:
                    io.writeln(
                        '<fg=black;bg=yellow>'
                        'Skipping virtualenv creation, '
                        'as specified in config file.'
                        '</>'
                    )

                    return cls()

                io.writeln(
                    f'Creating virtualenv <info>{name}</> in {str(venv_path)}'
                )
                builder = EnvBuilder(with_pip=True)
                builder.create(str(venv))
            else:
                if io.is_very_verbose():
                    io.writeln(f'Virtualenv <info>{name}</> already exists.')

            os.environ['VIRTUAL_ENV'] = str(venv)

        # venv detection:
        # stdlib venv may symlink sys.executable, so we can't use realpath.
        # but others can symlink *to* the venv Python,
        # so we can't just use sys.executable.
        # So we just check every item in the symlink tree (generally <= 3)
        p = os.path.normcase(sys.executable)
        paths = [p]
        while os.path.islink(p):
            p = os.path.normcase(
                os.path.join(os.path.dirname(p), os.readlink(p)))
            paths.append(p)

        p_venv = os.path.normcase(os.environ['VIRTUAL_ENV'])
        if any(p.startswith(p_venv) for p in paths):
            # Running properly in the virtualenv, don't need to do anything
            return cls()

        venv = os.environ['VIRTUAL_ENV']

        return cls(venv)

    @property
    def venv(self):
        return self._venv

    @property
    def python(self) -> str:
        """
        Path to current python executable
        """
        return self._bin('python')

    @property
    def pip(self) -> str:
        """
        Path to current pip executable
        """
        return self._bin('pip')

    @property
    def version_info(self):
        if self._version_info is not None:
            return self._version_info

        if not self.is_venv():
            self._version_info = sys.version_info
        else:
            output = self.run('python', '--version')

            version = output.split(' ')
            self._version_info = version[1].strip().split('.')

        return self._version_info

    def run(self, bin: str, *args, **kwargs) -> str:
        """
        Run a command inside the virtual env.
        """
        cmd = [self._bin(bin)] + list(args)

        try:
            output = subprocess.check_output(
                cmd, stderr=subprocess.STDOUT,
                **kwargs
            )
        except CalledProcessError as e:
            raise VenvCommandError(e)

        return output.decode()

    def exec(self, bin, *args, **kwargs):
        if not self.is_venv():
            return subprocess.run([bin] + list(args)).returncode
        else:
            with self.temp_environ():
                os.environ['PATH'] = self._path()
                os.environ['VIRTUAL_ENV'] = str(self._venv)

                self.unset_env('PYTHONHOME')
                self.unset_env('__PYVENV_LAUNCHER__')

                completed = subprocess.run([bin] + list(args), **kwargs)

                return completed.returncode

    @contextmanager
    def temp_environ(self):
        environ = dict(os.environ)
        try:
            yield
        finally:
            os.environ.clear()
            os.environ.update(environ)

    def _path(self):
        return os.pathsep.join([
            str(self._bin_dir),
            os.environ['PATH'],
        ])

    def unset_env(self, key):
        if key in os.environ:
            del os.environ[key]

    def get_shell(self):
        shell = Path(os.environ.get('SHELL', '')).stem
        if shell in ('bash', 'zsh', 'fish'):
            return shell

    def _bin(self, bin) -> str:
        """
        Return path to the given executable.
        """
        if not self.is_venv():
            return bin

        return str(self._bin_dir / bin)

    def is_venv(self) -> bool:
        return self._venv is not None


class NullVenv(Venv):

    def __init__(self, execute=False):
        super().__init__()

        self.executed = []
        self._execute = execute

    def run(self, bin: str, *args):
        self.executed.append([bin] + list(args))

        if self._execute:
            return super().run(bin, *args)

    def _bin(self, bin):
        return bin
