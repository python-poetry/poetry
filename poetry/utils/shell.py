import os

from shellingham import detect_shell
from shellingham import ShellDetectionFailure


class Shell:
    """
    Represents the current shell.
    """

    _shell = None

    def __init__(self, name, path):  # type: (str, str) -> None
        self._name = name
        self._path = path

    @property
    def name(self):  # type: () -> str
        return self._name

    @property
    def path(self):  # type: () -> str
        return self._path

    @classmethod
    def get(cls):  # type: () -> Shell
        """
        Retrieve the current shell.
        """
        if cls._shell is not None:
            return cls._shell

        try:
            name, path = detect_shell(os.getpid())
        except (RuntimeError, ShellDetectionFailure):
            raise RuntimeError("Unable to detect the current shell.")

        cls._shell = cls(name, path)

        return cls._shell

    def __repr__(self):  # type: () -> str
        return '{}("{}", "{}")'.format(self.__class__.__name__, self._name, self._path)
