<<<<<<< HEAD
=======
# -*- coding: utf-8 -*-
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
)


setup(**kwargs)
