import re
import subprocess


class GitConfig:

    def __init__(self):
        config_list = subprocess.check_output(
            ['git', 'config', '-l'],
            stderr=subprocess.STDOUT
        ).decode()

        self._config = {}

        m = re.findall('(?ms)^([^=]+)=(.*?)$', config_list)
        if m:
            for group in m:
                self._config[group[0]] = group[1]

    def get(self, key, default=None):
        return self._config.get(key, default)

    def __getitem__(self, item):
        return self._config[item]


class Git:

    def __init__(self, work_dir=None):
        self._config = GitConfig()
        self._work_dir = work_dir

    @property
    def config(self) -> GitConfig:
        return self._config

    def clone(self, repository, dest) -> str:
        return self.run('clone', repository, dest)

    def checkout(self, rev, folder=None) -> str:
        args = []
        if folder is None and self._work_dir:
            folder = self._work_dir

        if folder:
            args += [
                '--git-dir', (folder / '.git').as_posix(),
                '--work-tree', folder.as_posix()
            ]

        args += [
            'checkout', rev
        ]

        return self.run(*args)

    def rev_parse(self, rev, folder=None) -> str:
        args = []
        if folder is None and self._work_dir:
            folder = self._work_dir

        if folder:
            args += [
                '--git-dir', (folder / '.git').as_posix(),
                '--work-tree', folder.as_posix()
            ]

        args += [
            'rev-parse', rev
        ]

        return self.run(*args)

    def get_ignored_files(self, folder=None) -> list:
        args = []
        if folder is None and self._work_dir:
            folder = self._work_dir

        if folder:
            args += [
                '--git-dir', (folder / '.git').as_posix(),
                '--work-tree', folder.as_posix()
            ]

        args += [
            'ls-files', '--others', '-i', '--exclude-standard'
        ]
        output = self.run(*args)

        return output.split('\n')

    def run(self, *args) -> str:
        return subprocess.check_output(
            ['git'] + list(args),
            stderr=subprocess.STDOUT
        ).decode()
