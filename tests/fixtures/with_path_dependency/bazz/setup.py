from __future__ import annotations

from distutils.core import setup


setup(
    name="bazz",
    version="1",
    py_modules=["demo"],
    package_dir={"src": "src"},
    install_requires=["requests~=2.25.1"],
)
