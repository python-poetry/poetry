from .include import Include


class PackageInclude(Include):
    def __init__(self, base, include, formats=None, source=None):
        self._package = None
        self._is_package = False
        self._is_module = False
        self._source = source

        if source is not None:
            base = base / source

        super(PackageInclude, self).__init__(base, include, formats=formats)
        self.check_elements()

    @property
    def package(self):  # type: () -> str
        return self._package

    @property
    def source(self):  # type: () -> str
        return self._source

    def is_package(self):  # type: () -> bool
        return self._is_package

    def is_module(self):  # type: () -> bool
        return self._is_module

    def refresh(self):  # type: () -> PackageInclude
        super(PackageInclude, self).refresh()

        return self.check_elements()

    def check_elements(self):  # type: () -> PackageInclude
        root = self._elements[0]

        if not self._elements:
            raise ValueError(
                "{} does not contain any element".format(self._base / self._include)
            )

        if len(self._elements) > 1:
            # Probably glob
            self._is_package = True

            # Packages no longer need an __init__.py in python3, but there must
            # at least be one .py file for it to be considered a package
            if not any([element.suffix == ".py" for element in self._elements]):
                raise ValueError("{} is not a package.".format(root.name))

            self._package = root.parent.name
        else:
            if root.is_dir():
                # If it's a directory, we include everything inside it
                self._package = root.name
                self._elements = sorted(list(root.glob("**/*")))

                if not any([element.suffix == ".py" for element in self._elements]):
                    raise ValueError("{} is not a package.".format(root.name))

                self._is_package = True
            else:
                self._package = root.stem
                self._is_module = True

        return self
