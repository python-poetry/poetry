from typing import TYPE_CHECKING

from poetry.plugins.base_plugin import BasePlugin


if TYPE_CHECKING:
    from cleo.io.io import IO

    from poetry.poetry import Poetry


class Plugin(BasePlugin):
    """
    Generic plugin not related to the console application.
    The activate() method must be implemented and receives
    the Poetry instance.
    """

    type = "plugin"

    def activate(self, poetry: "Poetry", io: "IO") -> None:
        raise NotImplementedError()
