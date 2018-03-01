from poetry.utils.venv import Venv

from .base_installer import BaseInstaller


class PipInstaller(BaseInstaller):

    def __init__(self, venv: Venv, io):
        self._venv = venv
        self._io = io

    def install(self, package):
        args = ['install', self.requirement(package), '--no-deps']
        if package.source_type == 'legacy' and package.source_url:
            args += ['--index-url', package.source_url]

        self.run(*args)

    def update(self, source, target):
        args = ['install', self.requirement(target), '--no-deps', '-U']
        if target.source_type == 'legacy' and target.source_url:
            args += ['--index-url', target.source_url]

        self.run('install', self.requirement(target), '--no-deps', '-U')

    def remove(self, package):
        self.run('uninstall', package.name, '-y')

    def run(self, *args) -> str:
        return self._venv.run('pip', *args)

    def requirement(self, package) -> str:
        if package.source_type == 'git':
            return f'git+{package.source_url}@{package.source_reference}' \
                   f'#egg={package.name}'

        return f'{package.name}=={package.version}'
