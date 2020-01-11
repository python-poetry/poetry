from typing import TYPE_CHECKING
from typing import Optional

from poetry.console.commands.command import Command


if TYPE_CHECKING:
    from poetry.bundle.bundler_manager import BundlerManager


class BundleCommand(Command):
    """
    Base class for all bundle commands.
    """

    def __init__(self) -> None:
        self._bundler_manager: Optional["BundlerManager"] = None

        super().__init__()

    @property
    def bundler_manager(self) -> "BundlerManager":
        return self._bundler_manager

    def set_bundler_manager(self, bundler_manager: "BundlerManager") -> None:
        self._bundler_manager = bundler_manager
