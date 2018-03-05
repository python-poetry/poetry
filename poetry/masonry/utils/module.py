from pathlib import Path

from poetry.utils.helpers import module_name


class Module:

    def __init__(self, name, directory='.'):
        self._name = module_name(name)

        # It must exist either as a .py file or a directory, but not both
        pkg_dir = Path(directory, self._name)
        py_file = Path(directory, self._name + '.py')
        if pkg_dir.is_dir() and py_file.is_file():
            raise ValueError("Both {} and {} exist".format(pkg_dir, py_file))
        elif pkg_dir.is_dir():
            self._path = pkg_dir
            self._is_package = True
        elif py_file.is_file():
            self._path = py_file
            self._is_package = False
        else:
            raise ValueError("No file/folder found for package {}".format(name))

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> Path:
        return self._path

    @property
    def file(self) -> Path:
        if self._is_package:
            return self._path / '__init__.py'
        else:
            return self._path

    def is_package(self) -> bool:
        return self._is_package
