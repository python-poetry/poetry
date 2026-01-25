# Poetry: Python packaging and dependency management made easy and cool

[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![Stable Version](https://img.shields.io/pypi/v/poetry?label=stable)][PyPI Releases]
[![Pre-release Version](https://img.shields.io/github/v/release/python-poetry/poetry?label=pre-release&include_prereleases&sort=semver)][PyPI Releases]
[![Python Versions](https://img.shields.io/pypi/pyversions/poetry)][PyPI]
[![Download Stats](https://img.shields.io/pypi/dm/poetry)](https://pypistats.org/packages/poetry)
[![Discord](https://img.shields.io/discord/487711540787675139?logo=discord)][Discord]

Poetry helps you declare, manage and install dependencies of Python projects,
ensuring you have the right stack everywhere.

![Poetry Install](https://raw.githubusercontent.com/python-poetry/poetry/main/assets/install.gif)

Poetry replaces `setup.py`, `requirements.txt`, `setup.cfg`, `MANIFEST.in` and `Pipfile` with a simple `pyproject.toml`
based project format.

```toml
[project]
name = "my-package"
version = "0.1.0"
description = "The description of the package"

license = { text = "MIT" }
readme = "README.md"

# No python upper bound for package metadata
requires-python = ">=3.9"

authors = [
    { name = "Sébastien Eustace", email = "sebastien@eustace.io" },
]

# Keywords (translated to tags on the package index)
keywords = ["packaging", "poetry"]

dependencies = [
    # equivalent to ^3.8.1 with semver constraints
    "aiohttp (>=3.8.1,<4.0.0)",
    # dependency with extras
    "requests[security] (>=2.28,<3.0)",
    # version-specific dependency with prereleases allowed (see below)
    "tomli (>=2.0.1,<3.0.0) ; python_version < '3.11'",
    # git dependency with branch specified
    "cleo @ git+https://github.com/python-poetry/cleo.git@main",
]

[project.urls]
repository = "https://github.com/python-poetry/poetry"
homepage = "https://python-poetry.org"

# Scripts are easily expressed
[project.scripts]
my_package_cli = 'my_package.console:run'

[project.optional-dependencies]
# optional dependency to be installed via 'poetry install -E my-extra'
my-extra = ["pendulum (>=3.1.0,<4.0.0)"]

[tool.poetry.dependencies]
# Python upper bound for locking
python = ">=3.9,<4.0"
# Version-specific dependencies with prereleases allowed
tomli = { allow-prereleases = true }

# Dependency groups are supported for organizing your dependencies
[tool.poetry.group.dev.dependencies]
pytest = "^7.1.2"
pytest-cov = "^3.0"

# ...and can be installed only when explicitly requested
# via 'poetry install --with docs'
[tool.poetry.group.docs]
optional = true
[tool.poetry.group.docs.dependencies]
Sphinx = "^5.1.1"
```

## Installation

Poetry supports multiple installation methods, including a simple script found at [install.python-poetry.org]. For full
installation instructions, including advanced usage of the script, alternate install methods, and CI best practices, see
the full [installation documentation].

## Documentation

[Documentation] for the current version of Poetry (as well as the development branch and recently out of support
versions) is available from the [official website].

## Contribute

Poetry is a large, complex project always in need of contributors. For those new to the project, a list of
[suggested issues] to work on in Poetry and poetry-core is available. The full [contributing documentation] also
provides helpful guidance.

## Resources

* [Releases][PyPI Releases]
* [Official Website]
* [Documentation]
* [Issue Tracker]
* [Discord]

  [PyPI]: https://pypi.org/project/poetry/
  [PyPI Releases]: https://pypi.org/project/poetry/#history
  [Official Website]: https://python-poetry.org
  [Documentation]: https://python-poetry.org/docs/
  [Issue Tracker]: https://github.com/python-poetry/poetry/issues
  [Suggested Issues]: https://github.com/python-poetry/poetry/contribute
  [Contributing Documentation]: https://python-poetry.org/docs/contributing
  [Discord]: https://discord.com/invite/awxPgve
  [install.python-poetry.org]: https://install.python-poetry.org
  [Installation Documentation]: https://python-poetry.org/docs/#installation

## Related Projects

* [poetry-core](https://github.com/python-poetry/poetry-core): PEP 517 build-system for Poetry projects, and
dependency-free core functionality of the Poetry frontend
* [poetry-plugin-export](https://github.com/python-poetry/poetry-plugin-export): Export Poetry projects/lock files to
foreign formats like requirements.txt
* [poetry-plugin-bundle](https://github.com/python-poetry/poetry-plugin-bundle): Install Poetry projects/lock files to
external formats like virtual environments
* [install.python-poetry.org](https://github.com/python-poetry/install.python-poetry.org): The official Poetry
installation script
* [website](https://github.com/python-poetry/website): The official Poetry website and blog

## Supporters

Thanks to [JetBrains](https://www.jetbrains.com) for supporting us with licenses for their tools.

[<img src="https://resources.jetbrains.com/storage/products/company/brand/logos/jetbrains.svg" width="150" alt="JetBrains logo." />](https://www.jetbrains.com)
