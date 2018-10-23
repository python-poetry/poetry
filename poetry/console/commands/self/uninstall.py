import os
import shutil
import sys


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


PRE_UNINSTALL_MESSAGE = """# We are sorry to see you go!

This will uninstall {poetry}.

It will remove the `poetry` command from {poetry}'s bin directory, located at:

{poetry_home_bin}

This will also remove {poetry} from your system's PATH.
"""


class SelfUninstallCommand(Command):
    """
    Uninstalls poetry.

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

        if not self.option("yes"):
            if not self.confirm(
                "<question>Are you sure you want to uninstall Poetry?</>", False
            ):
                return

        self.remove_home()
        self.remove_from_path()

    def display_pre_uninstall_message(self):
        home_bin = self.POETRY_BIN
        if self.WINDOWS:
            home_bin = home_bin.replace(os.getenv("USERPROFILE", ""), "%USERPROFILE%")
        else:
            home_bin = home_bin.replace(os.getenv("HOME", ""), "$HOME")

        self.line(
            PRE_UNINSTALL_MESSAGE.format(
                poetry="<info>Poetry</info>",
                poetry_home_bin="<comment>{}</comment>".format(home_bin),
            )
        )

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

    def get_windows_path_var(self):
        with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as root:
            with winreg.OpenKey(root, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
                path, _ = winreg.QueryValueEx(key, "PATH")

                return path

    def set_windows_path_var(self, value):
        import ctypes

        with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as root:
            with winreg.OpenKey(root, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
                winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, value)

        # Tell other processes to update their environment
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x1A

        SMTO_ABORTIFHUNG = 0x0002

        result = ctypes.c_long()
        SendMessageTimeoutW = ctypes.windll.user32.SendMessageTimeoutW
        SendMessageTimeoutW(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            u"Environment",
            SMTO_ABORTIFHUNG,
            5000,
            ctypes.byref(result),
        )

    def remove_from_unix_path(self):
        pass
