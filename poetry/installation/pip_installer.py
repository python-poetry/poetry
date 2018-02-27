from poetry.utils.venv import Venv


class PipInstaller:

    def __init__(self, venv: Venv, io):
        self._venv = venv
        self._io = io

    def install(self, package):
        self.run('install', self.requirement(package), '--no-deps')

    def update(self, source, target):
        self.run('install', self.requirement(target), '--no-deps', '-U')

    def remove(self, package):
        self.run('uninstall', package.name, '-y')

    def run(self, *args) -> str:
        return self._venv.run('pip', *args)

    def requirement(self, package) -> str:
        return f'{package.name}=={package.version}'
