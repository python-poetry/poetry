from __future__ import annotations

from setuptools import find_packages
from setuptools import setup


setup(
    name="namespace_package_one",
    version="1.0.0",
    description="",
    long_description="",
    author="Python Poetry",
    author_email="noreply@python-poetry.org",
    license="MIT",
    packages=find_packages(),
    namespace_packages=["namespace_package"],
    zip_safe=False,
)
