from .operation import Operation


class Install(Operation):

    def __init__(self, package, reason: str = None) -> None:
        super().__init__(reason)

        self._package = package

    @property
    def package(self):
        return self._package

    @property
    def job_type(self):
        return 'install'

    def __str__(self) -> str:
        return 'Installing {} ({})'.format(
            self.package.pretty_name,
            self.format_version(self.package)
        )

    def __repr__(self):
        return '<Install {} ({})>'.format(
            self.package.pretty_name,
            self.format_version(self.package)
        )
