# -*- coding: utf-8 -*-

from setuptools import setup


kwargs = dict(
    name="demo",
    license="MIT",
    version="0.1.0",
    description="Demo project.",
    author="Sébastien Eustace",
    author_email="sebastien@eustace.io",
    url="https://github.com/demo/demo",
    packages=["my_package"],
    install_requires=[
        'cleo; extra == "foo"',
        "pendulum (>=1.4.4)",
        'tomlkit; extra == "bar"',
    ],
)


setup(**kwargs)
