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

    def __init__(self):
        self._config = GitConfig()

    @property
    def config(self) -> GitConfig:
        return self._config

    def clone(self, repository, dest) -> str:
        return self.run('clone', repository, dest)

    def checkout(self, rev, folder) -> str:
        return self.run(
            '--git-dir', (folder / '.git').as_posix(),
            '--work-tree', folder.as_posix(),
            'checkout', rev
        )

    def rev_parse(self, rev, folder) -> str:
        return self.run(
            '--git-dir', (folder / '.git').as_posix(),
            '--work-tree', folder.as_posix(),
            'rev-parse', rev
        )

    def get_ignored_files(self) -> list:
        output = self.run(
            'ls-files', '--others', '-i', '--exclude-standard'
        )

        return output.split('\n')

    def run(self, *args) -> str:
        return subprocess.check_output(
            ['git'] + list(args),
            stderr=subprocess.STDOUT
        ).decode()
