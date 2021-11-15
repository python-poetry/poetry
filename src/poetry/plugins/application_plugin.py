from .base_plugin import BasePlugin


class ApplicationPlugin(BasePlugin):
    """
    Base class for plugins.
    """

    type = "application.plugin"

    def activate(self, application):
        raise NotImplementedError()
