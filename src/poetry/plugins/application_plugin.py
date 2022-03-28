from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.plugins.base_plugin import BasePlugin


if TYPE_CHECKING:
    from poetry.console.application import Application


class ApplicationPlugin(BasePlugin):
    """
    Base class for plugins.
    """

    type = "application.plugin"

    def activate(self, application: Application) -> None:
        raise NotImplementedError()
