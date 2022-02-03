from __future__ import annotations

from setuptools import setup


tests_require = ["pytest"]

setup(
    name="extras_require_with_vars",
    version="0.0.1",
    description="test setup_reader.py",
    install_requires=[],
    extras_require={"test": tests_require},
)
