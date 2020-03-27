# -*- coding: utf-8 -*-

from .layout import Layout


DEFAULT = u"""__version__ = '{version}'
"""


class StandardLayout(Layout):
    def _create_default(self, path):
        package_path = path / self._package_name

        package_init = package_path / "__init__.py"

        package_path.mkdir()

        with package_init.open("w", encoding="utf-8") as f:
            f.write(DEFAULT.format(version=self._version))
