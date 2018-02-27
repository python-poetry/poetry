from poetry.utils.venv import Venv


class PipInstaller:

    def __init__(self, venv: Venv, io):
        self._venv = venv
        self._io = io

    def install(self, package):
        self._io.writeln(
            f'  - Installing <info>{package.name}</> '
            f'(<comment>{package.full_pretty_version}</>)'
        )

        self.run('install', self.requirement(package), '--no-deps')

    def update(self, source, target):
        self._io.writeln(
            f'  - Updating <info>{target.name}</> '
            f'(<comment>{source.pretty_version}</>'
            f' -> <comment>{target.pretty_version}</>)'
        )

        self.run('install', self.requirement(target), '--no-deps', '-U')

    def remove(self, package):
        self._io.writeln(
            f'  - Removing <info>{package.name}</> '
            f'(<comment>{package.full_pretty_version}</>)'
        )

        self.run('uninstall', package.name)

    def run(self, *args) -> str:
        return self._venv.run('pip', *args)

    def requirement(self, package) -> str:
        return f'{package.name}=={package.version}'
