from typing import Type

from poetry.layouts.layout import Layout
from poetry.layouts.src import SrcLayout


_LAYOUTS = {"src": SrcLayout, "standard": Layout}


def layout(name: str) -> Type[Layout]:
    if name not in _LAYOUTS:
        raise ValueError("Invalid layout")

    return _LAYOUTS[name]
