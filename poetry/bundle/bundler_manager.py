from typing import TYPE_CHECKING
from typing import Dict
from typing import List

from .exceptions import BundlerManagerError


if TYPE_CHECKING:
    from .bundler import Bundler


class BundlerManager(object):
    def __init__(self) -> None:
        from .venv_bundler import VenvBundler

        self._bundlers: Dict[str, "Bundler"] = {}

        # Register default bundlers
        self.register_bundler(VenvBundler())

    @property
    def bundlers(self) -> List["Bundler"]:
        return list(self._bundlers.values())

    def bundler(self, name: str) -> "Bundler":
        if name.lower() not in self._bundlers:
            raise BundlerManagerError('The bundler "{}" does not exist.'.format(name))

        return self._bundlers[name.lower()]

    def register_bundler(self, bundler: "Bundler") -> "BundlerManager":
        if bundler.name.lower() in self._bundlers:
            raise BundlerManagerError(
                'A bundler with the name "{}" already exists.'.format(bundler.name)
            )

        self._bundlers[bundler.name.lower()] = bundler

        return self
