from .operation import Operation


class Install(Operation):
    def __init__(self, package, reason=None, priority=0):
        super(Install, self).__init__(reason, priority=priority)

        self._package = package

    @property
    def package(self):
        return self._package

    @property
    def job_type(self):
        return "install"

    def __str__(self):
        return "Installing {} ({})".format(
            self.package.pretty_name, self.format_version(self.package)
        )

    def __repr__(self):
        return "<Install {} ({})>".format(
            self.package.pretty_name, self.format_version(self.package)
        )
