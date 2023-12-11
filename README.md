# Poetry: Python packaging and dependency management made easy

[![Stable Version](https://img.shields.io/pypi/v/poetry?label=stable)][PyPI Releases]
[![Pre-release Version](https://img.shields.io/github/v/release/python-poetry/poetry?label=pre-release&include_prereleases&sort=semver)][PyPI Releases]
[![Python Versions](https://img.shields.io/pypi/pyversions/poetry)][PyPI]
[![Download Stats](https://img.shields.io/pypi/dm/poetry)](https://pypistats.org/packages/poetry)
[![Discord](https://img.shields.io/discord/487711540787675139?logo=discord)][Discord]

Poetry helps you declare, manage and install dependencies of Python projects,
ensuring you have the right stack everywhere.

![Poetry Install](https://raw.githubusercontent.com/python-poetry/poetry/master/assets/install.gif)

Poetry replaces `setup.py`, `requirements.txt`, `setup.cfg`, `MANIFEST.in` and `Pipfile` with a simple `pyproject.toml`
based project format.

```toml
[tool.poetry]
name = "my-package"
version = "0.1.0"
description = "The description of the package"

license = "MIT"

authors = [
    "Sébastien Eustace <sebastien@eustace.io>"
]

repository = "https://github.com/python-poetry/poetry"
homepage = "https://python-poetry.org"

# README file(s) are used as the package description
readme = ["README.md", "LICENSE"]

# Keywords (translated to tags on the package index)
keywords = ["packaging", "poetry"]

[tool.poetry.dependencies]
# Compatible Python versions
python = ">=3.8"
# Standard dependency with semver constraints
aiohttp = "^3.8.1"
# Dependency with extras
requests = { version = "^2.28", extras = ["security"] }
# Version-specific dependencies with prereleases allowed
tomli = { version = "^2.0.1", python = "<3.11", allow-prereleases = true }
# Git dependencies
cleo = { git = "https://github.com/python-poetry/cleo.git", branch = "master" }
# Optional dependencies (installed by extras)
pendulum = { version = "^2.1.2", optional = true }

# Dependency groups are supported for organizing your dependencies
[tool.poetry.group.dev.dependencies]
pytest = "^7.1.2"
pytest-cov = "^3.0"

# ...and can be installed only when explicitly requested
[tool.poetry.group.docs]
optional = true
[tool.poetry.group.docs.dependencies]
Sphinx = "^5.1.1"

# Python-style entrypoints and scripts are easily expressed
[tool.poetry.scripts]
my-script = "my_package:main"
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

## How to test in a Repl

There are 2 ways to test poetry in a Repl.

## Method 1

1. Uncomment `PYTHONPATH = "$PYTHONPATH:$REPL_HOME/src"` in `.replit`
2. create a test project via:
    * mkdir proj
    * cd proj
    * poetry init # and go through the prompts
3. Run `python -m poetry ...`

This will install libs into `.pythonlibs`, but has the shortcoming that poetry won't distinguish its
own dependencies from the test project's.

## Method 2

1. Comment out `PYTHONPATH = "$PYTHONPATH:$REPL_HOME/src"` in `.replit`
2. create a test project via:
    * mkdir proj
    * cd proj
    * poetry init # and go through the prompts
3. cd ..
4. ./install_poetry_in_venv.sh
5. cd proj
6. Run `../poetry_env/bin/poetry ...`

This will also install libs into `.pythonlibs`, which will belong solely to the test project. Poetry's
dependencies live inside poetry_env.

If you want to "reset" the libs you can:

1. cd proj
2. rm poetry.lock
3. rm -fr ../.pythonlibs
4. rm -fr ../.cache/pypoetry
5. rid pyproject.toml of previously installed libraries
6. Now you can test installing stuff as if starting from scratch

## Bundle

For the Replit [Python Nix modules](https://github.com/replit/nixmodules/tree/main/pkgs/modules/python), we build a separate Poetry bundle for each supported version of Python 
containing Poetry plus all its dependencies and uploaded it to gcf. To build a bundle:

1. Make sure you have the correct version of Python and Pip, and that they match.
2. Get access to the latest version of poetry.
3. If you are working in a Repl, using a Python Nix module should give you all 3.
4. Run `build-bundle.sh`
5. It should produce a file `poetry-${VERSION}-python-${PYTHON_VERSION}-bundle.tgz` in `dist`
6. Upload this to gcf in the `poetry-bundles` of the Goval project.
7. Click on the ... and choose "Copy Public URL" for use in the poetry derivation back in
[Nix modules](https://github.com/replit/nixmodules)