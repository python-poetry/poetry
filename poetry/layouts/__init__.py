from typing import Type

from .layout import Layout
from .standard import StandardLayout


_LAYOUTS = {
    'standard': StandardLayout
}


def layout(name: str) -> Type[Layout]:
    if name not in _LAYOUTS:
        raise ValueError('Invalid layout')

    return _LAYOUTS[name]
