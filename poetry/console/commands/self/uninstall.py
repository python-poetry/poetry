import os
import platform
import shutil
import sys

from io import UnsupportedOperation

try:
    input = raw_input
except NameError:
    pass


try:
    try:
        import winreg
    except ImportError:
        import _winreg as winreg
except ImportError:
    winreg = None

from ..command import Command


def expanduser(path):
    """
    Expand ~ and ~user constructions.

    Includes a workaround for http://bugs.python.org/issue14768
    """
    expanded = os.path.expanduser(path)
    if path.startswith("~/") and expanded.startswith("//"):
        expanded = expanded[1:]

    return expanded


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


PRE_UNINSTALL_MESSAGE = """# We are sorry to see you go!

This will uninstall {poetry}.

It will remove the `poetry` command from {poetry}'s bin directory, located at:

{poetry_home_bin}

This will also remove {poetry} from your system's PATH.
"""


class SelfUninstallCommand(Command):
    """
    Uninstall poetry.

    self:uninstall
        { --y|yes : Accept all. }
    """

    WINDOWS = sys.platform.startswith("win") or (
        sys.platform == "cli" and os.name == "nt"
    )
    HOME = expanduser("~")
    POETRY_HOME = os.path.join(HOME, ".poetry")
    POETRY_BIN = os.path.join(POETRY_HOME, "bin")

    def handle(self):
        self.display_pre_uninstall_message()

        if not self.customize_uninstall():
            return

        self.remove_home()
        self.remove_from_path()

    def display_pre_uninstall_message(self):
        home_bin = self.POETRY_BIN
        if self.WINDOWS:
            home_bin = home_bin.replace(os.getenv("USERPROFILE", ""), "%USERPROFILE%")
        else:
            home_bin = home_bin.replace(os.getenv("HOME", ""), "$HOME")

        kwargs = {
            "poetry": colorize("info", "Poetry"),
            "poetry_home_bin": colorize("comment", home_bin),
        }

        print(PRE_UNINSTALL_MESSAGE.format(**kwargs))

    def customize_uninstall(self):
        if not self.option("yes"):
            print()

            uninstall = (
                input("Are you sure you want to uninstall Poetry? (y/[n]) ") or "n"
            )
            if uninstall.lower() not in {"y", "yes"}:
                return False

            print("")

        return True

    def remove_home(self):
        """
        Removes $POETRY_HOME.
        """
        if not os.path.exists(self.POETRY_HOME):
            return

        shutil.rmtree(self.POETRY_HOME)

    def remove_from_path(self):
        if self.WINDOWS:
            return self.remove_from_windows_path()

        return self.remove_from_unix_path()

    def remove_from_windows_path(self):
        path = self.get_windows_path_var()

        poetry_path = self.POETRY_BIN
        if poetry_path in path:
            path = path.replace(self.POETRY_BIN + ";", "")

            if poetry_path in path:
                path = path.replace(self.POETRY_BIN, "")

        self.set_windows_path_var(path)

    def remove_from_unix_path(self):
        pass
