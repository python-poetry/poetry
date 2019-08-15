# -*- coding: utf-8 -*-
from distutils.core import setup

packages = ["project_with_extras"]

package_data = {"": ["*"]}

extras_require = {"extras_a": ["pendulum>=1.4.4"], "extras_b": ["cachy>=0.2.0"]}

setup_kwargs = {
    "name": "project-with-extras",
    "version": "1.2.3",
    "description": "This is a description",
    "long_description": None,
    "author": "Your Name",
    "author_email": "you@example.com",
    "url": None,
    "packages": packages,
    "package_data": package_data,
    "extras_require": extras_require,
}


setup(**setup_kwargs)
