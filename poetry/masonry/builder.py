from .builders import CompleteBuilder
from .builders import SdistBuilder
from .builders import WheelBuilder


class Builder:

    _FORMATS = {"sdist": SdistBuilder, "wheel": WheelBuilder, "all": CompleteBuilder}

    def __init__(self, poetry, venv, io):
        self._poetry = poetry
        self._venv = venv
        self._io = io

    def build(self, fmt):
        if fmt not in self._FORMATS:
            raise ValueError("Invalid format: {}".format(fmt))

        builder = self._FORMATS[fmt](self._poetry, self._venv, self._io)

        return builder.build()
