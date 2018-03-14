import glob
import os
import subprocess
import sys

from subprocess import CalledProcessError


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
        self._version_info = None

    @classmethod
    def create(cls) -> 'Venv':
        if 'VIRTUAL_ENV' not in os.environ:
            # Not in a virtualenv
            return cls()

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

        if sys.platform == "win32":
            venv = os.path.join(
                os.environ['VIRTUAL_ENV'], 'Lib', 'site-packages'
            )
        else:
            lib = os.path.join(
                os.environ['VIRTUAL_ENV'], 'lib'
            )

            python = glob.glob(
                os.path.join(lib, 'python*')
            )[0].replace(
                lib + '/', ''
            )

            venv = os.path.join(
                lib,
                python,
                'site-packages'
            )

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

    def _bin(self, bin) -> str:
        """
        Return path to the given executable.
        """
        if not self.is_venv():
            return bin

        return os.path.realpath(
            os.path.join(self._venv, '..', '..', '..', 'bin', bin)
        )

    def is_venv(self) -> bool:
        return self._venv is not None
