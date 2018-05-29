# -*- coding: utf-8 -*-

from .layout import Layout

DEFAULT = u"""__version__ = '{version}'
"""


class SrcLayout(Layout):
    def _create_default(self, path):
        package_path = path / "src" / self._package_name

        package_init = package_path / "__init__.py"

        package_path.mkdir(parents=True)

        with package_init.open("w") as f:
            f.write(DEFAULT.format(version=self._version))
