class IncompatibilityCause(Exception):
    """
    The reason and Incompatibility's terms are incompatible.
    """


class RootCause(IncompatibilityCause):

    pass


class NoVersionsCause(IncompatibilityCause):

    pass


class DependencyCause(IncompatibilityCause):

    pass


class ConflictCause(IncompatibilityCause):
    """
    The incompatibility was derived from two existing incompatibilities
    during conflict resolution.
    """

    def __init__(self, conflict, other):
        self._conflict = conflict
        self._other = other

    @property
    def conflict(self):
        return self._conflict

    @property
    def other(self):
        return self._other

    def __str__(self):
        return str(self._conflict)


class PythonCause(IncompatibilityCause):
    """
    The incompatibility represents a package's python constraint
    (Python versions) being incompatible
    with the current python version.
    """

    def __init__(self, python_version, root_python_version):
        self._python_version = python_version
        self._root_python_version = root_python_version

    @property
    def python_version(self):
        return self._python_version

    @property
    def root_python_version(self):
        return self._root_python_version


class PlatformCause(IncompatibilityCause):
    """
    The incompatibility represents a package's platform constraint
    (OS most likely) being incompatible with the current platform.
    """

    def __init__(self, platform):
        self._platform = platform

    @property
    def platform(self):
        return self._platform


class PackageNotFoundCause(IncompatibilityCause):
    """
    The incompatibility represents a package that couldn't be found by its
    source.
    """

    def __init__(self, error):
        self._error = error

    @property
    def error(self):
        return self._error
