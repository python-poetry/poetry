from .include import Include


class PackageInclude(Include):
    def __init__(self, base, include, source=None):
        self._package = None
        self._is_package = False
        self._is_module = False
        self._source = source

        if source is not None:
            base = base / source

        super(PackageInclude, self).__init__(base, include)

        self.check_elements()

    @property
    def package(self):  # type: () -> str
        return self._package

    @property
    def source(self):  # type: () -> str
        return self._source

    def is_package(self):  # type: () -> bool
        return self._is_package

    def is_module(self):  # type: ()
        return self._is_module

    def refresh(self):  # type: () -> PackageInclude
        super(PackageInclude, self).refresh()

        return self.check_elements()

    def check_elements(self):  # type: () -> PackageInclude
        if not self._elements:
            raise ValueError(
                "{} does not contain any element".format(self._base / self._include)
            )

        if len(self._elements) > 1:
            # Probably glob
            self._is_package = True

            # The __init__.py file should be first
            root = self._elements[0]
            if root.name != "__init__.py":
                raise ValueError("{} is not a package.".format(root))

            self._package = root.parent.name
        else:
            if self._elements[0].is_dir():
                # If it's a directory, we include everything inside it
                self._package = self._elements[0].name
                self._elements = sorted(list(self._elements[0].glob("**/*")))
                self._is_package = True
            else:
                self._package = self._elements[0].stem
                self._is_module = True

        return self
