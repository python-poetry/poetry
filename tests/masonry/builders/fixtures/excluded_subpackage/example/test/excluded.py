from __future__ import annotations

from tests.masonry.builders.fixtures.excluded_subpackage.example import __version__


def test_version():
    assert __version__ == "0.1.0"
