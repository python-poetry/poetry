import os
from setuptools import setup, find_packages


def get_version():
    basedir = os.path.dirname(__file__)
    with open(os.path.join(basedir, 'poetry/__version__.py')) as f:
        variables = {}
        exec(f.read(), variables)

        version = variables.get('__version__')
        if version:
            return version

    raise RuntimeError('No version info found.')


__version__ = get_version()

packages = ['poetry']
for pkg in find_packages('poetry'):
    packages.append('poetry.' + pkg)

kwargs = dict(
    name='poetry',
    license='MIT',
    version=__version__,
    description='Python dependency management and packaging made easy.',
    long_description=open('README.rst').read(),
    author='Sébastien Eustace',
    author_email='sebastien@eustace.io',
    url='https://github.com/sdispater/poetry',
    packages=packages,
    python_requires='>=3.6.0',
    install_requires=[
        'cleo>=0.6.1,<0.7.0',
        'requests>=2.18.0,<3.0.0',
        'toml>=0.9.4,<0.10.0',
        'cachy>=0.1.0,<0.2.0',
        'pip-tools>=1.11.0,<2.0.0'
    ],
    include_package_data=True,
    tests_require=['pytest>=3.4.0,<3.5.0'],
    classifiers=[
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    entry_points={
        'console_scripts': ['poetry = poetry:console.run']
    }
)


setup(**kwargs)
