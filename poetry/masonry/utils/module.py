import os

from poetry.utils._compat import Path
from poetry.utils.helpers import module_name


class Module:
    def __init__(self, package, directory="."):
        self._name = module_name(package.name)
        self._in_src = False

        # It must exist either as a .py file or a directory, but not both
        pkg_dir = Path(directory, self._name)
        py_file = Path(directory, self._name + ".py")
        if pkg_dir.is_dir() and py_file.is_file():
            raise ValueError("Both {} and {} exist".format(pkg_dir, py_file))
        elif pkg_dir.is_dir():
            self._path = pkg_dir
            self._is_package = True
        elif py_file.is_file():
            self._path = py_file
            self._is_package = False
        elif package.module is not None:
            module_pkg_dir = Path(directory, package.module.replace(".", os.sep))
            module_py_file = Path(
                directory, package.module.replace(".", os.sep) + ".py"
            )

            if module_pkg_dir.is_dir() and module_py_file.is_file():
                raise ValueError(
                    "Both {} and {} exist".format(module_pkg_dir, module_py_file)
                )
            elif module_pkg_dir.is_dir():
                self._path = module_pkg_dir
                self._is_package = True
            elif module_py_file.is_file():
                self.path = module_py_file
                self._is_package = False
            else:
                raise ValueError(
                    "No module found for {} or {}".format(
                        module_pkg_dir, module_py_file
                    )
                )
        else:
            # Searching for a src module
            src_pkg_dir = Path(directory, "src", self._name)
            src_py_file = Path(directory, "src", self._name + ".py")

            if src_pkg_dir.is_dir() and src_py_file.is_file():
                raise ValueError(
                    "Both {} and {} exist".format(src_pkg_dir, src_py_file)
                )
            elif src_pkg_dir.is_dir():
                self._in_src = True
                self._path = src_pkg_dir
                self._is_package = True
            elif src_py_file.is_file():
                self._in_src = True
                self._path = src_py_file
                self._is_package = False
            else:
                raise ValueError(
                    "No file/folder found for package {}".format(self._name)
                )

    @property
    def name(self):  # type: () -> str
        return self._name

    @property
    def path(self):  # type: () -> Path
        return self._path

    @property
    def file(self):  # type: () -> Path
        if self._is_package:
            return self._path / "__init__.py"
        else:
            return self._path

    def is_package(self):  # type: () -> bool
        return self._is_package

    def is_in_src(self):  # type: () -> bool
        return self._in_src
