# -*- coding: utf-8 -*-
from setuptools import setup


kwargs = dict(
    name="demo",
    license="MIT",
    version="0.1.2",
    description="Demo project.",
    author="Sébastien Eustace",
    author_email="sebastien@eustace.io",
    url="https://github.com/demo/demo",
    packages=["demo"],
    install_requires=["pendulum>=1.4.4"],
    extras_require={"foo": ["cleo"], "bar": ["tomlkit"]},
)


setup(**kwargs)
