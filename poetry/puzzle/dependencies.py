class Dependencies:
    """
    Proxy to package dependencies to only require them when needed.
    """

    def __init__(self, package, provider):
        self._package = package
        self._provider = provider
        self._dependencies = None

    @property
    def dependencies(self):
        if self._dependencies is None:
            self._dependencies = self._get_dependencies()

        return self._dependencies

    def _get_dependencies(self):
        self._provider.debug("Getting dependencies for {}".format(self._package), 0)
        dependencies = self._provider._dependencies_for(self._package)

        if dependencies is None:
            dependencies = []

        return dependencies

    def __len__(self):
        return len(self.dependencies)

    def __iter__(self):
        return self.dependencies.__iter__()

    def __add__(self, other):
        return self.dependencies + other

    __radd__ = __add__
