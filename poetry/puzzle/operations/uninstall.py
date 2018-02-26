from .operation import Operation


class Uninstall(Operation):

    def __init__(self, package, reason=None):
        super(Uninstall, self).__init__(reason)

        self._package = package

    @property
    def package(self):
        return self._package

    @property
    def job_type(self):
        return 'uninstall'

    def __str__(self):
        return 'Uninstalling {} ({})'.format(
            self.package.pretty_name,
            self.format_version(self._package)
        )

    def __repr__(self):
        return '<Uninstall {} ({})>'.format(
            self.package.pretty_name,
            self.format_version(self.package)
        )
