"""
This script will install poetry and its dependencies
in isolation from the rest of the system.

It does, in order:

  - Downloads the latest stable (or pre-release) version of poetry.
  - Downloads all its dependencies in the poetry/_vendor directory.
  - Copies it and all extra files in $POETRY_HOME.
  - Updates the PATH in a system-specific way.

There will be a `poetry` script that will be installed in $POETRY_HOME/bin
which will act as the poetry command but is slightly different in the sense
that it will use the current Python installation.

What this means is that one Poetry installation can serve for multiple
Python versions.
"""
import argparse
import ast
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile

from contextlib import contextmanager
from email.parser import Parser
from functools import cmp_to_key
from glob import glob

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

try:
    input = raw_input
except NameError:
    pass


WINDOWS = sys.platform.startswith("win") or (sys.platform == "cli" and os.name == "nt")


FOREGROUND_COLORS = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37,
}

BACKGROUND_COLORS = {
    "black": 40,
    "red": 41,
    "green": 42,
    "yellow": 43,
    "blue": 44,
    "magenta": 45,
    "cyan": 46,
    "white": 47,
}

OPTIONS = {"bold": 1, "underscore": 4, "blink": 5, "reverse": 7, "conceal": 8}


def style(fg, bg, options):
    codes = []

    if fg:
        codes.append(FOREGROUND_COLORS[fg])

    if bg:
        codes.append(BACKGROUND_COLORS[bg])

    if options:
        if not isinstance(options, (list, tuple)):
            options = [options]

        for option in options:
            codes.append(OPTIONS[option])

    return "\033[{}m".format(";".join(map(str, codes)))


STYLES = {
    "info": style("green", None, None),
    "comment": style("yellow", None, None),
    "error": style("red", None, None),
    "warning": style("yellow", None, None),
}


def is_decorated():
    if platform.system().lower() == "windows":
        return (
            os.getenv("ANSICON") is not None
            or "ON" == os.getenv("ConEmuANSI")
            or "xterm" == os.getenv("Term")
        )

    if not hasattr(sys.stdout, "fileno"):
        return False

    try:
        return os.isatty(sys.stdout.fileno())
    except UnsupportedOperation:
        return False


def colorize(style, text):
    if not is_decorated():
        return text

    return "{}{}\033[0m".format(STYLES[style], text)


@contextmanager
def temporary_directory(*args, **kwargs):
    try:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory(*args, **kwargs) as name:
            yield name
    except ImportError:
        name = tempfile.mkdtemp(*args, **kwargs)

        yield name

        shutil.rmtree(name)


def expanduser(path):
    """
    Expand ~ and ~user constructions.

    Includes a workaround for http://bugs.python.org/issue14768
    """
    expanded = os.path.expanduser(path)
    if path.startswith("~/") and expanded.startswith("//"):
        expanded = expanded[1:]

    return expanded


HOME = expanduser("~")
POETRY_HOME = os.path.join(HOME, ".poetry")
POETRY_BIN = os.path.join(POETRY_HOME, "bin")
POETRY_ENV = os.path.join(POETRY_HOME, "env")
POETRY_LIB = os.path.join(POETRY_HOME, "lib")
POETRY_LIB_BACKUP = os.path.join(POETRY_HOME, "lib-backup")


BIN = """#!/usr/bin/env python
import sys
import os

lib = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, lib)

if __name__ == "__main__":
    from poetry.console import main

    main()
"""


PRE_MESSAGE = """# Welcome to {poetry}!

This will download and install the latest version of {poetry},
a dependency and package manager for Python.

It will add the `poetry` command to {poetry}'s bin directory, located at:

{poetry_home_bin}

{platform_msg}

You can uninstall at any time with `poetry self:uninstall`,
or by executing this script with the --uninstall option,
and these changes will be reverted.
"""


PRE_MESSAGE_UNIX = """This path will then be added to your `PATH` environment variable by
modifying the profile file{plural} located at:

{rcfiles}"""


PRE_MESSAGE_WINDOWS = """This path will then be added to your `PATH` environment variable by
modifying the `HKEY_CURRENT_USER/Environment/PATH` registry key."""

PRE_MESSAGE_NO_MODIFY_PATH = """This path needs to be in your `PATH` environment variable,
but will not be added automatically."""

POST_MESSAGE_UNIX = """{poetry} ({version}) is installed now. Great!

To get started you need {poetry}'s bin directory ({poetry_home_bin}) in your `PATH`
environment variable. Next time you log in this will be done
automatically.

To configure your current shell run `source {poetry_home_env}`
"""

POST_MESSAGE_WINDOWS = """{poetry} ({version}) is installed now. Great!

To get started you need Poetry's bin directory ({poetry_home_bin}) in your `PATH`
environment variable. Future applications will automatically have the
correct environment, but you may need to restart your current shell.
"""

POST_MESSAGE_UNIX_NO_MODIFY_PATH = """{poetry} ({version}) is installed now. Great!

To get started you need {poetry}'s bin directory ({poetry_home_bin}) in your `PATH`
environment variable.

To configure your current shell run `source {poetry_home_env}`
"""

POST_MESSAGE_WINDOWS_NO_MODIFY_PATH = """{poetry} ({version}) is installed now. Great!

To get started you need Poetry's bin directory ({poetry_home_bin}) in your `PATH`
environment variable. This has not been done automatically.
"""


class Installer:

    CURRENT_PYTHON = sys.executable
    METADATA_URL = "https://pypi.org/pypi/poetry/json"
    VERSION_REGEX = re.compile(
        "v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?"
        "("
        "[._-]?"
        "(?:(stable|beta|b|RC|alpha|a|patch|pl|p)((?:[.-]?\d+)*)?)?"
        "([.-]?dev)?"
        ")?"
        "(?:\+[^\s]+)?"
    )

    def __init__(self, version=None, preview=False, force=False):
        self._version = version
        self._preview = preview
        self._force = force
        self._modify_path = True

    def allows_prereleases(self):
        return self._preview

    def run(self):
        version, current_version = self.get_version()

        if version is None:
            return 0

        self.customize_install()
        self.display_pre_message()
        self.ensure_home()

        try:
            self.install(version, upgrade=current_version is not None)
        except subprocess.CalledProcessError as e:
            print(colorize("error", "An error has occured: {}".format(str(e))))
            print(e.output.decode())

            return e.returncode

        self.display_post_message(version)

        return 0

    def get_version(self):
        print(colorize("info", "Retrieving Poetry metadata"))

        r = urlopen(self.METADATA_URL)
        metadata = json.loads(r.read().decode())
        r.close()

        def _compare_versions(x, y):
            mx = self.VERSION_REGEX.match(x)
            my = self.VERSION_REGEX.match(y)

            vx = tuple(int(p) for p in mx.groups()[:3]) + (mx.group(5),)
            vy = tuple(int(p) for p in my.groups()[:3]) + (my.group(5),)

            if vx < vy:
                return -1
            elif vx > vy:
                return 1

            return 0

        print("")
        releases = sorted(
            metadata["releases"].keys(), key=cmp_to_key(_compare_versions)
        )

        if self._version and self._version not in releases:
            print(colorize("error", "Version {} does not exist.".format(self._version)))

            return None, None

        version = self._version
        if not version:
            for release in reversed(releases):
                m = self.VERSION_REGEX.match(release)
                if m.group(5) and not self.allows_prereleases():
                    continue

                version = release

                break

        current_version = None
        if os.path.exists(POETRY_LIB):
            with open(os.path.join(POETRY_LIB, "poetry", "__version__.py")) as f:
                version_content = f.read()

            current_version_re = re.match(
                '(?ms).*__version__ = "(.+)".*', version_content
            )
            if not current_version_re:
                print(
                    colorize(
                        "warning",
                        "Unable to get the current Poetry version. Assuming None",
                    )
                )
            else:
                current_version = current_version_re.group(1)

        if current_version == version and not self._force:
            print("Latest version already installed.")
            return None, current_version

        return version, current_version

    def customize_install(self):
        print(
            """Before we start, please answer the following questions.
You may simple press the Enter key to keave unchanged.
"""
        )

        modify_path = input("Modify PATH variable? ([y]/n)") or "y"
        if modify_path.lower() in {"n", "no"}:
            self._modify_path = False

        print("")

    def ensure_home(self):
        """
        Ensures that $POETRY_HOME exists or create it.
        """
        if not os.path.exists(POETRY_HOME):
            os.mkdir(POETRY_HOME, 0o755)

    def install(self, version, upgrade=False):
        """
        Installs Poetry in $POETRY_HOME.
        """
        print("Installing version: " + colorize("info", version))

        self.make_lib(version)
        self.make_bin()
        self.make_env()
        self.update_path()

        return 0

    def make_lib(self, version):
        """
        Packs everything into a single lib/ directory.
        """
        if os.path.exists(POETRY_LIB):
            # Backup the current installation
            if os.path.exists(POETRY_LIB_BACKUP):
                shutil.rmtree(POETRY_LIB_BACKUP)

            shutil.copytree(POETRY_LIB, POETRY_LIB_BACKUP)
            shutil.rmtree(POETRY_LIB)

        try:
            self._make_lib(version)
        except Exception:
            if os.path.exists(POETRY_LIB):
                shutil.rmtree(POETRY_LIB)

            if not os.path.exists(POETRY_LIB_BACKUP):
                raise

            shutil.copytree(POETRY_LIB_BACKUP, POETRY_LIB)

            raise

        if os.path.exists(POETRY_LIB_BACKUP):
            shutil.rmtree(POETRY_LIB_BACKUP)

    def _make_lib(self, version):
        # Most of the work will be delegated to pip
        with temporary_directory(prefix="poetry-installer-") as dir:
            dist = os.path.join(dir, "dist")
            print("  - Getting dependencies")
            try:
                self.call(
                    self.CURRENT_PYTHON,
                    "-m",
                    "pip",
                    "install",
                    "poetry=={}".format(version),
                    "--target",
                    dist,
                )
            except subprocess.CalledProcessError as e:
                if "must supply either home or prefix/exec-prefix" in e.output.decode():
                    # Homebrew Python and possible other installations
                    # We workaround this issue by temporarily changing
                    # the --user directory
                    original_user = os.getenv("PYTHONUSERBASE")
                    os.environ["PYTHONUSERBASE"] = dir
                    self.call(
                        self.CURRENT_PYTHON,
                        "-m",
                        "pip",
                        "install",
                        "poetry=={}".format(version),
                        "--user",
                        "--ignore-installed",
                    )

                    if original_user is not None:
                        os.environ["PYTHONUSERBASE"] = original_user
                    else:
                        del os.environ["PYTHONUSERBASE"]

                    # Finding site-package directory
                    lib = os.path.join(dir, "lib")
                    lib_python = list(glob(os.path.join(lib, "python*")))[0]
                    site_packages = os.path.join(lib_python, "site-packages")
                    shutil.copytree(site_packages, dist)
                else:
                    raise

            print("  - Vendorizing dependencies")

            poetry_dir = os.path.join(dist, "poetry")
            vendor_dir = os.path.join(poetry_dir, "_vendor")

            # Everything, except poetry itself, should
            # be put in the _vendor directory
            for file in glob(os.path.join(dist, "*")):
                if (
                    os.path.basename(file).startswith("poetry")
                    or os.path.basename(file) == "__pycache__"
                ):
                    continue

                dest = os.path.join(vendor_dir, os.path.basename(file))
                if os.path.isdir(file):
                    shutil.copytree(file, dest)
                    shutil.rmtree(file)
                else:
                    shutil.copy(file, dest)
                    os.unlink(file)

            shutil.copytree(dist, POETRY_LIB)

    def make_bin(self):
        if not os.path.exists(POETRY_BIN):
            os.mkdir(POETRY_BIN, 0o755)

        if not WINDOWS:
            with open(os.path.join(POETRY_BIN, "poetry"), "w") as f:
                f.write(BIN)

            # Making the file executable
            st = os.stat(os.path.join(POETRY_BIN, "poetry"))
            os.chmod(os.path.join(POETRY_BIN, "poetry"), st.st_mode | stat.S_IEXEC)

    def make_env(self):
        if WINDOWS:
            return

        with open(os.path.join(POETRY_HOME, "env"), "w") as f:
            f.write(self.get_export_string())

    def update_path(self):
        """
        Tries to update the $PATH automatically.
        """
        if WINDOWS:
            return self._update_windows_path()

        # Updating any profile we can on UNIX systems
        export_string = self.get_export_string()

        addition = "\n{}".format(export_string)

        updated = []
        profiles = self.get_unix_profiles()
        for profile in profiles:
            if not os.path.exists(profile):
                continue

            with open(profile, "r") as f:
                content = f.read()

            if addition not in content:
                with open(profile, "a") as f:
                    f.write(addition)

                updated.append(os.path.relpath(profile, HOME))

    def get_export_string(self):
        path = POETRY_BIN.replace(os.getenv("HOME", ""), "$HOME")
        export_string = 'export PATH="{}:$PATH"'.format(path)

        return export_string

    def get_unix_profiles(self):
        profiles = [os.path.join(HOME, ".profile")]

        shell = os.getenv("SHELL")
        if "zsh" in shell:
            zdotdir = os.getenv("ZDOTDIR", HOME)
            profiles.append(os.path.join(zdotdir, ".zprofile"))

        bash_profile = os.path.join(HOME, ".bash_profile")
        if os.path.exists(bash_profile):
            profiles.append(bash_profile)

        return profiles

    def update_windows_path(self):
        return False

    def display_pre_message(self):
        kwargs = {
            "poetry": colorize("info", "Poetry"),
            "poetry_home_bin": colorize(
                "comment", POETRY_BIN.replace(os.getenv("HOME", ""), "$HOME")
            ),
        }

        if not self._modify_path:
            kwargs["platform_msg"] = PRE_MESSAGE_NO_MODIFY_PATH
        else:
            if WINDOWS:
                kwargs["platform_msg"] = PRE_MESSAGE_WINDOWS
            else:
                profiles = [
                    colorize("comment", p.replace(os.getenv("HOME", ""), "$HOME"))
                    for p in self.get_unix_profiles()
                ]
                kwargs["platform_msg"] = PRE_MESSAGE_UNIX.format(
                    rcfiles="\n".join(profiles), plural="s" if len(profiles) > 1 else ""
                )

        print(PRE_MESSAGE.format(**kwargs))

    def display_post_message(self, version):
        print("")

        kwargs = {
            "poetry": colorize("info", "Poetry"),
            "poetry_home_bin": colorize(
                "comment", POETRY_BIN.replace(os.getenv("HOME", ""), "$HOME")
            ),
            "poetry_home_env": colorize(
                "comment", POETRY_ENV.replace(os.getenv("HOME", ""), "$HOME")
            ),
            "version": colorize("comment", version),
        }

        if WINDOWS:
            message = POST_MESSAGE_WINDOWS
            if not self._modify_path:
                message = POST_MESSAGE_WINDOWS_NO_MODIFY_PATH
        else:
            message = POST_MESSAGE_UNIX
            if not self._modify_path:
                message = POST_MESSAGE_UNIX_NO_MODIFY_PATH

        print(message.format(**kwargs))

    def call(self, *args):
        return subprocess.check_output(args, stderr=subprocess.STDOUT)


def main():
    parser = argparse.ArgumentParser(
        description="Installs the latest (or given) version of poetry"
    )
    parser.add_argument(
        "-p", "--preview", dest="preview", action="store_true", default=False
    )
    parser.add_argument("--version", dest="version")
    parser.add_argument(
        "-f", "--force", dest="force", action="store_true", default=False
    )

    args = parser.parse_args()

    installer = Installer(
        version=args.version or os.getenv("POETRY_VERSION"),
        preview=args.preview or os.getenv("POETRY_PREVIEW"),
        force=args.force,
    )

    return installer.run()


if __name__ == "__main__":
    sys.exit(main())
