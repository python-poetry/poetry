# -*- coding: utf-8 -*-
import re
import subprocess


from poetry.utils._compat import decode


class GitConfig:
    def __init__(self, requires_git_presence=False):
        self._config = {}

        try:
            config_list = decode(
                subprocess.check_output(
                    ["git", "config", "-l"], stderr=subprocess.STDOUT
                )
            )

            m = re.findall("(?ms)^([^=]+)=(.*?)$", config_list)
            if m:
                for group in m:
                    self._config[group[0]] = group[1]
        except (subprocess.CalledProcessError, OSError):
            if requires_git_presence:
                raise

    def get(self, key, default=None):
        return self._config.get(key, default)

    def __getitem__(self, item):
        return self._config[item]


class Git:
    def __init__(self, work_dir=None):
        self._config = GitConfig(requires_git_presence=True)
        self._work_dir = work_dir

    @property
    def config(self):  # type: () -> GitConfig
        return self._config

    def clone(self, repository, dest):  # type: (...) -> str
        return self.run("clone", repository, str(dest))

    def checkout(self, rev, folder=None):  # type: (...) -> str
        args = []
        if folder is None and self._work_dir:
            folder = self._work_dir

        if folder:
            args += [
                "--git-dir",
                (folder / ".git").as_posix(),
                "--work-tree",
                folder.as_posix(),
            ]

        args += ["checkout", rev]

        return self.run(*args)

    def rev_parse(self, rev, folder=None):  # type: (...) -> str
        args = []
        if folder is None and self._work_dir:
            folder = self._work_dir

        if folder:
            args += [
                "--git-dir",
                (folder / ".git").as_posix(),
                "--work-tree",
                folder.as_posix(),
            ]

        args += ["rev-parse", rev]

        return self.run(*args)

    def get_ignored_files(self, folder=None):  # type: (...) -> list
        args = []
        if folder is None and self._work_dir:
            folder = self._work_dir

        if folder:
            args += [
                "--git-dir",
                (folder / ".git").as_posix(),
                "--work-tree",
                folder.as_posix(),
            ]

        args += ["ls-files", "--others", "-i", "--exclude-standard"]
        output = self.run(*args)

        return output.split("\n")

    def run(self, *args):  # type: (...) -> str
        return decode(
            subprocess.check_output(["git"] + list(args), stderr=subprocess.STDOUT)
        )
