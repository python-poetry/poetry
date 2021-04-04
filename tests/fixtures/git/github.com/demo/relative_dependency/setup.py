import os
from setuptools import setup

PKG_DIR = os.path.dirname(os.path.abspath(__file__))
setup(
    name="relative_dependency",
    version="0.1.0",
    install_requires=[
        f"subdir_package @ file://{PKG_DIR}/subdir_package"
    ]
)
