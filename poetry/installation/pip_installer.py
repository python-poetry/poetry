import os
import tempfile

from subprocess import CalledProcessError

from poetry.utils._compat import encode
from poetry.utils.venv import Venv

from .base_installer import BaseInstaller


class PipInstaller(BaseInstaller):

    def __init__(self, venv, io):  # type: (Venv, ...) -> None
        self._venv = venv
        self._io = io

    def install(self, package, update=False):
        args = ['install', '--no-deps']

        if package.source_type == 'legacy' and package.source_url:
            args += ['--index-url', package.source_url]

        if update:
            args.append('-U')

        if package.hashes and not package.source_type:
            # Format as a requirements.txt
            # We need to create a requirements.txt file
            # for each package in order to check hashes.
            # This is far from optimal but we do not have any
            # other choice since this is the only way for pip
            # to verify hashes.
            req = self.create_temporary_requirement(package)
            args += ['-r', req]

            try:
                self.run(*args)
            finally:
                os.unlink(req)
        else:
            args.append(self.requirement(package))

            self.run(*args)

    def update(self, _, target):
        self.install(target, update=True)

    def remove(self, package):
        try:
            self.run('uninstall', package.name, '-y')
        except CalledProcessError as e:
            if 'not installed' in str(e):
                return

            raise

    def run(self, *args, **kwargs):  # type: (...) -> str
        return self._venv.run('pip', *args, **kwargs)

    def requirement(self, package, formatted=False):
        if formatted and not package.source_type:
            req = '{}=={}'.format(package.name, package.version)
            for h in package.hashes:
                req += ' --hash sha256:{}'.format(h)

            req += '\n'

            return req

        if package.source_type in ['file', 'directory']:
            return os.path.realpath(package.source_reference)

        if package.source_type == 'git':
            return 'git+{}@{}#egg={}'.format(
                package.source_url,
                package.source_reference,
                package.name
            )

        return '{}=={}'.format(package.name, package.version)

    def create_temporary_requirement(self, package):
        fd, name = tempfile.mkstemp(
            'reqs.txt', '{}-{}'.format(package.name, package.version)
        )

        try:
            os.write(fd, encode(self.requirement(package, formatted=True)))
        finally:
            os.close(fd)

        return name
