from __future__ import annotations

import pytest


@pytest.fixture
def init_basic_inputs() -> str:
    return "\n".join(
        [
            "my-package",  # Package name
            "1.2.3",  # Version
            "This is a description",  # Description
            "n",  # Author
            "MIT",  # License
            ">=3.6",  # Python
            "n",  # Interactive packages
            "n",  # Interactive dev packages
            "\n",  # Generate
        ]
    )


@pytest.fixture()
def init_basic_toml() -> str:
    return """\
[project]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = [
    {name = "Your Name",email = "you@example.com"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.6"
"""
