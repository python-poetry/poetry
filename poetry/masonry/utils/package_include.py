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

    def is_stub_only(self):  # type: () -> bool
        # returns `True` if this a PEP 561 stub-only package,
        # see [PEP 561](https://www.python.org/dev/peps/pep-0561/#stub-only-packages)
        return self.package.endswith("-stubs") and all(
            el.suffix == ".pyi"
            or (el.parent.name == self.package and el.name == "py.typed")
            for el in self.elements
            if el.is_file()
        )

    def has_modules(self):  # type: () -> bool
        # Packages no longer need an __init__.py in python3, but there must
        # at least be one .py file for it to be considered a package
        return any(element.suffix == ".py" for element in self.elements)

    def check_elements(self):  # type: () -> PackageInclude
        if not self._elements:
            raise ValueError(
                "{} does not contain any element".format(self._base / self._include)
            )

        root = self._elements[0]
        if len(self._elements) > 1:
            # Probably glob
            self._is_package = True
            self._package = root.parent.name

            if not self.is_stub_only() and not self.has_modules():
                raise ValueError("{} is not a package.".format(root.name))

        else:
            if root.is_dir():
                # If it's a directory, we include everything inside it
                self._package = root.name
                self._elements = sorted(list(root.glob("**/*")))

                if not self.is_stub_only() and not self.has_modules():
                    raise ValueError("{} is not a package.".format(root.name))

                self._is_package = True
            else:
                self._package = root.stem
                self._is_module = True

        return self
