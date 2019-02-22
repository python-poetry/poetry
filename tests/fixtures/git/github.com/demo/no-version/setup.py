# -*- coding: utf-8 -*-
import ast
import os

from setuptools import setup


def read_version():
    with open(os.path.join(os.path.dirname(__file__), "demo", "__init__.py")) as f:
        for line in f:
            if line.startswith("__version__ = "):
                return ast.literal_eval(line[len("__version__ = ") :].strip())


kwargs = dict(
    name="demo",
    license="MIT",
    version=read_version(),
    description="Demo project.",
    author="Sébastien Eustace",
    author_email="sebastien@eustace.io",
    url="https://github.com/demo/demo",
    packages=["demo"],
    install_requires=["pendulum>=1.4.4"],
    extras_require={"foo": ["cleo"]},
)


setup(**kwargs)
