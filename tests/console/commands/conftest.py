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
            "~2.7 || ^3.6",  # Python
            "n",  # Interactive packages
            "n",  # Interactive dev packages
            "\n",  # Generate
        ]
    )


@pytest.fixture()
def init_basic_toml() -> str:
    return """\
[tool.poetry]
name = "my-package"
version = "1.2.3"
description = "This is a description"
authors = ["Your Name <you@example.com>"]
license = "MIT"
readme = "README.md"

[tool.poetry.dependencies]
python = "~2.7 || ^3.6"
"""
