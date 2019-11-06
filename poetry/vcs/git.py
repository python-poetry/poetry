# -*- coding: utf-8 -*-
import re
import subprocess

from collections import namedtuple

from poetry.utils._compat import decode


PATTERNS = [
    re.compile(
        r"^(git\+)?"
        r"(?P<protocol>https?|git|ssh|rsync|file)://"
        r"(?:(?P<user>.+)@)*"
        r"(?P<resource>[a-z0-9_.-]*)"
        r"(:?P<port>[\d]+)?"
        r"(?P<pathname>[:/]((?P<owner>[\w\-]+)/)?"
        r"((?P<name>[\w\-.]+?)(\.git|/)?)?)"
        r"([@#](?P<rev>[^@#]+))?"
        r"$"
    ),
    re.compile(
        r"(git\+)?"
        r"((?P<protocol>\w+)://)"
        r"((?P<user>\w+)@)?"
        r"(?P<resource>[\w.\-]+)"
        r"(:(?P<port>\d+))?"
        r"(?P<pathname>(/(?P<owner>\w+)/)"
        r"(/?(?P<name>[\w\-]+)(\.git|/)?)?)"
        r"([@#](?P<rev>[^@#]+))?"
        r"$"
    ),
    re.compile(
        r"^(?:(?P<user>.+)@)*"
        r"(?P<resource>[a-z0-9_.-]*)[:]*"
        r"(?P<port>[\d]+)?"
        r"(?P<pathname>/?(?P<owner>.+)/(?P<name>.+).git)"
        r"([@#](?P<rev>[^@#]+))?"
        r"$"
    ),
    re.compile(
        r"((?P<user>\w+)@)?"
        r"(?P<resource>[\w.\-]+)"
        r"[:/]{1,2}"
        r"(?P<pathname>((?P<owner>\w+)/)?"
        r"((?P<name>[\w\-]+)(\.git|/)?)?)"
        r"([@#](?P<rev>[^@#]+))?"
        r"$"
    ),
]


class ParsedUrl:
    def __init__(self, protocol, resource, pathname, user, port, name, rev):
        self.protocol = protocol
        self.resource = resource
        self.pathname = pathname
        self.user = user
        self.port = port
        self.name = name
        self.rev = rev

    @classmethod
    def parse(cls, url):  # type: () -> ParsedUrl
        for pattern in PATTERNS:
            m = pattern.match(url)
            if m:
                groups = m.groupdict()
                return ParsedUrl(
                    groups.get("protocol"),
                    groups.get("resource"),
                    groups.get("pathname"),
                    groups.get("user"),
                    groups.get("port"),
                    groups.get("name"),
                    groups.get("rev"),
                )

        raise ValueError('Invalid git url "{}"'.format(url))

    def format(self):
        return "{}{}{}{}{}".format(
            "{}://".format(self.protocol) if self.protocol else "",
            "{}@".format(self.user) if self.user else "",
            self.resource,
            ":{}".format(self.port) if self.port else "",
            "/" + self.pathname if self.pathname.startswith(":") else self.pathname,
            "#{}".format(self.rev) if self.rev else "",
        )

    def __str__(self):  # type: () -> str
        return self.format()


GitUrl = namedtuple("GitUrl", ["url", "revision"])


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

    @classmethod
    def normalize_url(cls, url):  # type: (str) -> GitUrl
        parsed = ParsedUrl.parse(url)

        formatted = re.sub(r"^git\+", "", url)
        if parsed.rev:
            formatted = re.sub(r"[#@]{}$".format(parsed.rev), "", formatted)

        altered = parsed.format() != formatted

        if altered:
            if re.match(r"^git\+https?", url) and re.match(
                r"^/?:[^0-9]", parsed.pathname
            ):
                normalized = re.sub(r"git\+(.*:[^:]+):(.*)", "\\1/\\2", url)
            elif re.match(r"^git\+file", url):
                normalized = re.sub(r"git\+", "", url)
            else:
                normalized = re.sub(r"^(?:git\+)?ssh://", "", url)
        else:
            normalized = parsed.format()

        return GitUrl(re.sub(r"#[^#]*$", "", normalized), parsed.rev)

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

    def remote_urls(self, folder=None):  # type: (...) -> dict
        output = self.run(
            "config", "--get-regexp", r"remote\..*\.url", folder=folder
        ).strip()

        urls = {}
        for url in output.splitlines():
            name, url = url.split(" ", 1)
            urls[name.strip()] = url.strip()

        return urls

    def remote_url(self, folder=None):  # type: (...) -> str
        urls = self.remote_urls(folder=folder)

        return urls.get("remote.origin.url", urls[list(urls.keys())[0]])

    def run(self, *args, **kwargs):  # type: (...) -> str
        folder = kwargs.pop("folder", None)
        if folder:
            args = (
                "--git-dir",
                (folder / ".git").as_posix(),
                "--work-tree",
                folder.as_posix(),
            ) + args

        return decode(
            subprocess.check_output(["git"] + list(args), stderr=subprocess.STDOUT)
        ).strip()
