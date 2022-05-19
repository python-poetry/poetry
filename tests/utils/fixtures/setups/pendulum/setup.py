from __future__ import annotations

from distutils.core import setup

from build import *  # nopycln: import


packages = [
    "pendulum",
    "pendulum._extensions",
    "pendulum.formatting",
    "pendulum.locales",
    "pendulum.locales.da",
    "pendulum.locales.de",
    "pendulum.locales.en",
    "pendulum.locales.es",
    "pendulum.locales.fa",
    "pendulum.locales.fo",
    "pendulum.locales.fr",
    "pendulum.locales.ko",
    "pendulum.locales.lt",
    "pendulum.locales.pt_br",
    "pendulum.locales.zh",
    "pendulum.mixins",
    "pendulum.parsing",
    "pendulum.parsing.exceptions",
    "pendulum.tz",
    "pendulum.tz.data",
    "pendulum.tz.zoneinfo",
    "pendulum.utils",
]

package_data = {"": ["*"]}

install_requires = ["python-dateutil>=2.6,<3.0", "pytzdata>=2018.3"]

extras_require = {':python_version < "3.5"': ["typing>=3.6,<4.0"]}

setup_kwargs = {
    "name": "pendulum",
    "version": "2.0.4",
    "description": "Python datetimes made easy",
    "author": "Sébastien Eustace",
    "author_email": "sebastien@eustace.io",
    "url": "https://pendulum.eustace.io",
    "packages": packages,
    "package_data": package_data,
    "install_requires": install_requires,
    "extras_require": extras_require,
    "python_requires": ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
}

build(setup_kwargs)

setup(**setup_kwargs)
