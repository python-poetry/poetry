from typing import Type

from .layout import Layout
from .src import SrcLayout
from .standard import StandardLayout


_LAYOUTS = {"src": SrcLayout, "standard": StandardLayout}


def layout(name):  # type: (str) -> Type[Layout]
    if name not in _LAYOUTS:
        raise ValueError("Invalid layout")

    return _LAYOUTS[name]
