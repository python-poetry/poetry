from .operation import Operation


class Update(Operation):

    def __init__(self, initial, target, reason=None):
        self._initial_package = initial
        self._target_package = target
        
        super(Update, self).__init__(reason)

    @property
    def initial_package(self):
        return self._initial_package

    @property
    def target_package(self):
        return self._target_package

    @property
    def job_type(self):
        return 'update'

    def __str__(self):
        return (
            'Updating {} ({}) to {} ({})'.format(
                self.initial_package.pretty_name,
                self.format_version(self.initial_package),
                self.target_package.pretty_name,
                self.format_version(self.target_package)
            )
        )

    def __repr__(self):
        return (
            '<Update {} ({}) to {} ({})>'.format(
                self.initial_package.pretty_name,
                self.format_version(self.initial_package),
                self.target_package.pretty_name,
                self.format_version(self.target_package)
            )
        )
