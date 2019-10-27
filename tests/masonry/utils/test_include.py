# -*- coding: utf-8 -*-
from tomlkit._compat import decode
from tomlkit._utils import escape_string
from tomlkit.items import String
from tomlkit.items import StringType
from tomlkit.items import Trivia

from poetry.masonry.utils.include import Include
from poetry.utils._compat import Path


def test_include_elements():
    def create_toml_string(value):
        escaped = escape_string(value)

        return String(StringType.SLB, decode(value), escaped, Trivia())

    include = Include(
        Path(__file__).parent / "fixtures" / "MyPackage", create_toml_string("Foo")
    )

    expected_path = Path(__file__).parent / Path("fixtures/MyPackage/Foo")

    assert len(include.elements) == 1
    assert include.elements[0] == expected_path
