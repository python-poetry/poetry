"""
This script will install Poetry and its dependencies.

It does, in order:

  - Downloads the virtualenv package to a temporary directory and add it to sys.path.
  - Creates a virtual environment in the correct OS data dir which will be
      - `%APPDATA%\\pypoetry` on Windows
      -  ~/Library/Application Support/pypoetry on MacOS
      - `${XDG_DATA_HOME}/pypoetry` (or `~/.local/share/pypoetry` if it's not set) on UNIX systems
      - In `${POETRY_HOME}` if it's set.
  - Installs the latest or given version of Poetry inside this virtual environment.
  - Installs a `poetry` script in the Python user directory (or `${POETRY_HOME/bin}` if `POETRY_HOME` is set).
"""

import argparse
import json
import os
import re
import shutil
import site
import subprocess
import sys
import tempfile

from contextlib import closing
from contextlib import contextmanager
from functools import cmp_to_key
from io import UnsupportedOperation
from pathlib import Path
from typing import Optional
from urllib.request import Request
from urllib.request import urlopen


SHELL = os.getenv("SHELL", "")
WINDOWS = sys.platform.startswith("win") or (sys.platform == "cli" and os.name == "nt")
MACOS = sys.platform == "darwin"

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
    "info": style("cyan", None, None),
    "comment": style("yellow", None, None),
    "success": style("green", None, None),
    "error": style("red", None, None),
    "warning": style("yellow", None, None),
    "b": style(None, None, ("bold",)),
}


def is_decorated():
    if WINDOWS:
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


def is_interactive():
    if not hasattr(sys.stdin, "fileno"):
        return False

    try:
        return os.isatty(sys.stdin.fileno())
    except UnsupportedOperation:
        return False


def colorize(style, text):
    if not is_decorated():
        return text

    return "{}{}\033[0m".format(STYLES[style], text)


def string_to_bool(value):
    value = value.lower()

    return value in {"true", "1", "y", "yes"}


def data_dir(version: Optional[str] = None) -> Path:
    if os.getenv("POETRY_HOME"):
        return Path(os.getenv("POETRY_HOME")).expanduser()

    if WINDOWS:
        const = "CSIDL_APPDATA"
        path = os.path.normpath(_get_win_folder(const))
        path = os.path.join(path, "pypoetry")
    elif MACOS:
        path = os.path.expanduser("~/Library/Application Support/pypoetry")
    else:
        path = os.getenv("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        path = os.path.join(path, "pypoetry")

    if version:
        path = os.path.join(path, version)

    return Path(path)


def bin_dir(version: Optional[str] = None) -> Path:
    if os.getenv("POETRY_HOME"):
        return Path(os.getenv("POETRY_HOME"), "bin").expanduser()

    user_base = site.getuserbase()

    if WINDOWS:
        bin_dir = os.path.join(user_base, "Scripts")
    else:
        bin_dir = os.path.join(user_base, "bin")

    return Path(bin_dir)


def _get_win_folder_from_registry(csidl_name):
    import winreg as _winreg

    shell_folder_name = {
        "CSIDL_APPDATA": "AppData",
        "CSIDL_COMMON_APPDATA": "Common AppData",
        "CSIDL_LOCAL_APPDATA": "Local AppData",
    }[csidl_name]

    key = _winreg.OpenKey(
        _winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
    )
    dir, type = _winreg.QueryValueEx(key, shell_folder_name)

    return dir


def _get_win_folder_with_ctypes(csidl_name):
    import ctypes

    csidl_const = {
        "CSIDL_APPDATA": 26,
        "CSIDL_COMMON_APPDATA": 35,
        "CSIDL_LOCAL_APPDATA": 28,
    }[csidl_name]

    buf = ctypes.create_unicode_buffer(1024)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl_const, None, 0, buf)

    # Downgrade to short path name if have highbit chars. See
    # <http://bugs.activestate.com/show_bug.cgi?id=85099>.
    has_high_char = False
    for c in buf:
        if ord(c) > 255:
            has_high_char = True
            break
    if has_high_char:
        buf2 = ctypes.create_unicode_buffer(1024)
        if ctypes.windll.kernel32.GetShortPathNameW(buf.value, buf2, 1024):
            buf = buf2

    return buf.value


if WINDOWS:
    try:
        from ctypes import windll  # noqa

        _get_win_folder = _get_win_folder_with_ctypes
    except ImportError:
        _get_win_folder = _get_win_folder_from_registry


@contextmanager
def temporary_directory(*args, **kwargs):
    try:
        from tempfile import TemporaryDirectory
    except ImportError:
        name = tempfile.mkdtemp(*args, **kwargs)

        yield name

        shutil.rmtree(name)
    else:
        with TemporaryDirectory(*args, **kwargs) as name:
            yield name


PRE_MESSAGE = """# Welcome to {poetry}!

This will download and install the latest version of {poetry},
a dependency and package manager for Python.

It will add the `poetry` command to {poetry}'s bin directory, located at:

{poetry_home_bin}

You can uninstall at any time by executing this script with the --uninstall option,
and these changes will be reverted.
"""

POST_MESSAGE = """{poetry} ({version}) is installed now. Great!

You can test that everything is set up by executing:

`{test_command}`
"""

POST_MESSAGE_NOT_IN_PATH = """{poetry} ({version}) is installed now. Great!

To get started you need {poetry}'s bin directory ({poetry_home_bin}) in your `PATH`
environment variable.
{configure_message}
Alternatively, you can call {poetry} explicitly with `{poetry_executable}`.

You can test that everything is set up by executing:

`{test_command}`
"""

POST_MESSAGE_CONFIGURE_UNIX = """
Add `export PATH="{poetry_home_bin}:$PATH"` to your shell configuration file.
"""

POST_MESSAGE_CONFIGURE_FISH = """
You can execute `set -U fish_user_paths {poetry_home_bin} $fish_user_paths`
"""

POST_MESSAGE_CONFIGURE_WINDOWS = """"""


class Cursor:
    def __init__(self) -> None:
        self._output = sys.stdout

    def move_up(self, lines: int = 1) -> "Cursor":
        self._output.write("\x1b[{}A".format(lines))

        return self

    def move_down(self, lines: int = 1) -> "Cursor":
        self._output.write("\x1b[{}B".format(lines))

        return self

    def move_right(self, columns: int = 1) -> "Cursor":
        self._output.write("\x1b[{}C".format(columns))

        return self

    def move_left(self, columns: int = 1) -> "Cursor":
        self._output.write("\x1b[{}D".format(columns))

        return self

    def move_to_column(self, column: int) -> "Cursor":
        self._output.write("\x1b[{}G".format(column))

        return self

    def move_to_position(self, column: int, row: int) -> "Cursor":
        self._output.write("\x1b[{};{}H".format(row + 1, column))

        return self

    def save_position(self) -> "Cursor":
        self._output.write("\x1b7")

        return self

    def restore_position(self) -> "Cursor":
        self._output.write("\x1b8")

        return self

    def hide(self) -> "Cursor":
        self._output.write("\x1b[?25l")

        return self

    def show(self) -> "Cursor":
        self._output.write("\x1b[?25h\x1b[?0c")

        return self

    def clear_line(self) -> "Cursor":
        """
        Clears all the output from the current line.
        """
        self._output.write("\x1b[2K")

        return self

    def clear_line_after(self) -> "Cursor":
        """
        Clears all the output from the current line after the current position.
        """
        self._output.write("\x1b[K")

        return self

    def clear_output(self) -> "Cursor":
        """
        Clears all the output from the cursors' current position
        to the end of the screen.
        """
        self._output.write("\x1b[0J")

        return self

    def clear_screen(self) -> "Cursor":
        """
        Clears the entire screen.
        """
        self._output.write("\x1b[2J")

        return self


class Installer:
    METADATA_URL = "https://pypi.org/pypi/poetry/json"
    VERSION_REGEX = re.compile(
        r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?"
        "("
        "[._-]?"
        r"(?:(stable|beta|b|rc|RC|alpha|a|patch|pl|p)((?:[.-]?\d+)*)?)?"
        "([.-]?dev)?"
        ")?"
        r"(?:\+[^\s]+)?"
    )

    def __init__(
        self,
        version: Optional[str] = None,
        preview: bool = False,
        force: bool = False,
        accept_all: bool = False,
        git: Optional[str] = None,
        path: Optional[str] = None,
    ) -> None:
        self._version = version
        self._preview = preview
        self._force = force
        self._accept_all = accept_all
        self._git = git
        self._path = path
        self._data_dir = data_dir()
        self._bin_dir = bin_dir()
        self._cursor = Cursor()

    def allows_prereleases(self) -> bool:
        return self._preview

    def run(self) -> int:
        if self._git:
            version = self._git
        elif self._path:
            version = self._path
        else:
            version, current_version = self.get_version()

        if version is None:
            return 0

        self.display_pre_message()
        self.ensure_directories()

        def _is_self_upgrade_supported(x):
            mx = self.VERSION_REGEX.match(x)

            if mx is None:
                # the version is not semver, perhaps scm or file, we assume upgrade is supported
                return True

            vx = tuple(int(p) for p in mx.groups()[:3]) + (mx.group(5),)
            return vx >= (1, 1, 7)

        if version and not _is_self_upgrade_supported(version):
            self._write(
                colorize(
                    "warning",
                    f"You are installing {version}. When using the current installer, this version does not support "
                    f"updating using the 'self update' command. Please use 1.1.7 or later.",
                )
            )
            if not self._accept_all:
                continue_install = input("Do you want to continue? ([y]/n) ") or "y"
                if continue_install.lower() in {"n", "no"}:
                    return 0

        try:
            self.install(version)
        except subprocess.CalledProcessError as e:
            print(
                colorize("error", f"\nAn error has occurred: {e}\n{e.stdout.decode()}")
            )

            return e.returncode

        self._write("")
        self.display_post_message(version)

        return 0

    def install(self, version, upgrade=False):
        """
        Installs Poetry in $POETRY_HOME.
        """
        self._write(
            "Installing {} ({})".format(
                colorize("info", "Poetry"), colorize("info", version)
            )
        )

        env_path = self.make_env(version)
        self.install_poetry(version, env_path)
        self.make_bin(version)

        self._overwrite(
            "Installing {} ({}): {}".format(
                colorize("info", "Poetry"),
                colorize("b", version),
                colorize("success", "Done"),
            )
        )

        self._data_dir.joinpath("VERSION").write_text(version)

        return 0

    def uninstall(self) -> int:
        if not self._data_dir.exists():
            self._write(
                "{} is not currently installed.".format(colorize("info", "Poetry"))
            )

            return 1

        version = None
        if self._data_dir.joinpath("VERSION").exists():
            version = self._data_dir.joinpath("VERSION").read_text().strip()

        if version:
            self._write(
                "Removing {} ({})".format(
                    colorize("info", "Poetry"), colorize("b", version)
                )
            )
        else:
            self._write("Removing {}".format(colorize("info", "Poetry")))

        shutil.rmtree(str(self._data_dir))
        for script in ["poetry", "poetry.bat"]:
            if self._bin_dir.joinpath(script).exists():
                self._bin_dir.joinpath(script).unlink()

        return 0

    def make_env(self, version: str) -> Path:
        self._overwrite(
            "Installing {} ({}): {}".format(
                colorize("info", "Poetry"),
                colorize("b", version),
                colorize("comment", "Creating environment"),
            )
        )

        env_path = self._data_dir.joinpath("venv")

        with temporary_directory() as tmp_dir:
            subprocess.call(
                [sys.executable, "-m", "pip", "install", "virtualenv", "-t", tmp_dir],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

            sys.path.insert(0, tmp_dir)

            import virtualenv

            virtualenv.cli_run([str(env_path), "--clear"])

        # We add a special file so that Poetry can detect
        # its own virtual environment
        env_path.joinpath("poetry_env").touch()

        return env_path

    def make_bin(self, version: str) -> None:
        self._overwrite(
            "Installing {} ({}): {}".format(
                colorize("info", "Poetry"),
                colorize("b", version),
                colorize("comment", "Creating script"),
            )
        )

        self._bin_dir.mkdir(parents=True, exist_ok=True)

        script = "poetry"
        target_script = "venv/bin/poetry"
        if WINDOWS:
            script = "poetry.exe"
            target_script = "venv/Scripts/poetry.exe"

        if self._bin_dir.joinpath(script).exists():
            self._bin_dir.joinpath(script).unlink()

        try:
            self._bin_dir.joinpath(script).symlink_to(
                self._data_dir.joinpath(target_script)
            )
        except OSError:
            # This can happen if the user
            # does not have the correct permission on Windows
            shutil.copy(
                self._data_dir.joinpath(target_script), self._bin_dir.joinpath(script)
            )

    def install_poetry(self, version: str, env_path: Path) -> None:
        self._overwrite(
            "Installing {} ({}): {}".format(
                colorize("info", "Poetry"),
                colorize("b", version),
                colorize("comment", "Installing Poetry"),
            )
        )

        if WINDOWS:
            python = env_path.joinpath("Scripts/python.exe")
        else:
            python = env_path.joinpath("bin/python")

        if self._git:
            specification = "git+" + version
        elif self._path:
            specification = version
        else:
            specification = f"poetry=={version}"

        subprocess.run(
            [str(python), "-m", "pip", "install", specification],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
        )

    def display_pre_message(self) -> None:
        kwargs = {
            "poetry": colorize("info", "Poetry"),
            "poetry_home_bin": colorize("comment", self._bin_dir),
        }
        self._write(PRE_MESSAGE.format(**kwargs))

    def display_post_message(self, version: str) -> None:
        if WINDOWS:
            return self.display_post_message_windows(version)

        if SHELL == "fish":
            return self.display_post_message_fish(version)

        return self.display_post_message_unix(version)

    def display_post_message_windows(self, version: str) -> None:
        path = self.get_windows_path_var()

        message = POST_MESSAGE_NOT_IN_PATH
        if path and str(self._bin_dir) in path:
            message = POST_MESSAGE

        self._write(
            message.format(
                poetry=colorize("info", "Poetry"),
                version=colorize("b", version),
                poetry_home_bin=colorize("comment", self._bin_dir),
                poetry_executable=colorize("b", self._bin_dir.joinpath("poetry")),
                configure_message=POST_MESSAGE_CONFIGURE_WINDOWS.format(
                    poetry_home_bin=colorize("comment", self._bin_dir)
                ),
                test_command=colorize("b", "poetry --version"),
            )
        )

    def get_windows_path_var(self) -> Optional[str]:
        import winreg

        with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as root:
            with winreg.OpenKey(root, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
                path, _ = winreg.QueryValueEx(key, "PATH")

                return path

    def display_post_message_fish(self, version: str) -> None:
        fish_user_paths = subprocess.check_output(
            ["fish", "-c", "echo $fish_user_paths"]
        ).decode("utf-8")

        message = POST_MESSAGE_NOT_IN_PATH
        if fish_user_paths and str(self._bin_dir) in fish_user_paths:
            message = POST_MESSAGE

        self._write(
            message.format(
                poetry=colorize("info", "Poetry"),
                version=colorize("b", version),
                poetry_home_bin=colorize("comment", self._bin_dir),
                poetry_executable=colorize("b", self._bin_dir.joinpath("poetry")),
                configure_message=POST_MESSAGE_CONFIGURE_FISH.format(
                    poetry_home_bin=colorize("comment", self._bin_dir)
                ),
                test_command=colorize("b", "poetry --version"),
            )
        )

    def display_post_message_unix(self, version: str) -> None:
        paths = os.getenv("PATH", "").split(":")

        message = POST_MESSAGE_NOT_IN_PATH
        if paths and str(self._bin_dir) in paths:
            message = POST_MESSAGE

        self._write(
            message.format(
                poetry=colorize("info", "Poetry"),
                version=colorize("b", version),
                poetry_home_bin=colorize("comment", self._bin_dir),
                poetry_executable=colorize("b", self._bin_dir.joinpath("poetry")),
                configure_message=POST_MESSAGE_CONFIGURE_UNIX.format(
                    poetry_home_bin=colorize("comment", self._bin_dir)
                ),
                test_command=colorize("b", "poetry --version"),
            )
        )

    def ensure_directories(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._bin_dir.mkdir(parents=True, exist_ok=True)

    def get_version(self):
        current_version = None
        if self._data_dir.joinpath("VERSION").exists():
            current_version = self._data_dir.joinpath("VERSION").read_text().strip()

        self._write(colorize("info", "Retrieving Poetry metadata"))

        metadata = json.loads(self._get(self.METADATA_URL).decode())

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

        self._write("")
        releases = sorted(
            metadata["releases"].keys(), key=cmp_to_key(_compare_versions)
        )

        if self._version and self._version not in releases:
            self._write(
                colorize("error", "Version {} does not exist.".format(self._version))
            )

            return None, None

        version = self._version
        if not version:
            for release in reversed(releases):
                m = self.VERSION_REGEX.match(release)
                if m.group(5) and not self.allows_prereleases():
                    continue

                version = release

                break

        if current_version == version and not self._force:
            self._write(
                "The latest version ({}) is already installed.".format(
                    colorize("b", version)
                )
            )

            return None, current_version

        return version, current_version

    def _write(self, line) -> None:
        sys.stdout.write(line + "\n")

    def _overwrite(self, line) -> None:
        if not is_decorated():
            return self._write(line)

        self._cursor.move_up()
        self._cursor.clear_line()
        self._write(line)

    def _get(self, url):
        request = Request(url, headers={"User-Agent": "Python Poetry"})

        with closing(urlopen(request)) as r:
            return r.read()


def main():
    parser = argparse.ArgumentParser(
        description="Installs the latest (or given) version of poetry"
    )
    parser.add_argument(
        "-p",
        "--preview",
        help="install preview version",
        dest="preview",
        action="store_true",
        default=False,
    )
    parser.add_argument("--version", help="install named version", dest="version")
    parser.add_argument(
        "-f",
        "--force",
        help="install on top of existing version",
        dest="force",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-y",
        "--yes",
        help="accept all prompts",
        dest="accept_all",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--uninstall",
        help="uninstall poetry",
        dest="uninstall",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--path",
        dest="path",
        action="store",
        help=(
            "Install from a given path (file or directory) instead of "
            "fetching the latest version of Poetry available online."
        ),
    )
    parser.add_argument(
        "--git",
        dest="git",
        action="store",
        help=(
            "Install from a git repository instead of fetching the latest version "
            "of Poetry available online."
        ),
    )

    args = parser.parse_args()

    installer = Installer(
        version=args.version or os.getenv("POETRY_VERSION"),
        preview=args.preview or string_to_bool(os.getenv("POETRY_PREVIEW", "0")),
        force=args.force,
        accept_all=args.accept_all
        or string_to_bool(os.getenv("POETRY_ACCEPT", "0"))
        or not is_interactive(),
        path=args.path,
        git=args.git,
    )

    if args.uninstall or string_to_bool(os.getenv("POETRY_UNINSTALL", "0")):
        return installer.uninstall()

    return installer.run()


if __name__ == "__main__":
    sys.exit(main())
