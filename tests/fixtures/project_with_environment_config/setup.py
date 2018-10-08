# -*- coding: utf-8 -*-
from distutils.core import setup

packages = \
['project_with_environment_config']

package_data = \
{'': ['*']}

setup_kwargs = {
    'name': 'project-with-environment-config',
    'version': '0.1.0',
    'description': 'Some description.',
    'long_description': 'My Package\n==========\n',
    'author': 'Jared Kofron',
    'author_email': 'jared.kofron@gmail.com',
    'url': 'https://poetry.eustace.io',
    'packages': packages,
    'package_data': package_data,
    'python_requires': '>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*',
}


setup(**setup_kwargs)
