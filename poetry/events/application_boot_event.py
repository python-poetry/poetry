from clikit.api.event import Event


class ApplicationBootEvent(Event):
    """
    Event triggered when the application before the application is booted.

    It receives an ApplicationConfig instance.
    """

    def __init__(self, config):
        super(ApplicationBootEvent, self).__init__()

        self._config = config

    @property
    def config(self):
        return self._config
