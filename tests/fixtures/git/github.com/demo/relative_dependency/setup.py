import os
from setuptools import setup

setup(
    name="relative_dependency",
    version="0.1.0",
    install_requires=[
        'subdir_package @ file://localhost/%s/subdir_package/' % os.getcwd().replace('\\', '/'),
    ]
)
