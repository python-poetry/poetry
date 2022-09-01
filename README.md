# Poetry: Dependency Management for Python

[![Tests Status](https://github.com/python-poetry/poetry/workflows/Tests/badge.svg?branch=master&event=push)](https://github.com/python-poetry/poetry/actions?query=workflow%3ATests+branch%3Amaster+event%3Apush)
[![Stable Version](https://img.shields.io/pypi/v/poetry?label=stable)](https://pypi.org/project/poetry/)
[![Pre-release Version](https://img.shields.io/github/v/release/python-poetry/poetry?label=pre-release&include_prereleases&sort=semver)](https://pypi.org/project/poetry/#history)
[![Downloads](https://img.shields.io/pypi/dm/poetry)](https://pypistats.org/packages/poetry)
[![Discord](https://img.shields.io/discord/487711540787675139?logo=discord)](https://discord.com/invite/awxPgve)

Poetry helps you declare, manage and install dependencies of Python projects,
ensuring you have the right stack everywhere.

It requires Python 3.7+ to run.

![Poetry Install](https://raw.githubusercontent.com/python-poetry/poetry/master/assets/install.gif)

## Documentation

The [complete documentation](https://python-poetry.org/docs/) is available on the [official website](https://python-poetry.org).

## Installation

Instructions on how to install `poetry` can be found [here](https://python-poetry.org/docs/#installation).
You can also refer [here](https://python-poetry.org/docs/#enable-tab-completion-for-bash-fish-or-zsh) for
information on how to enable tab completion in your environment.

## Introduction

`poetry` is a tool to handle dependency installation as well as building and packaging of Python packages.
It only needs one file to do all of that: the new, [standardized](https://www.python.org/dev/peps/pep-0518/) `pyproject.toml`.

In other words, poetry uses `pyproject.toml` to replace `setup.py`, `requirements.txt`, `setup.cfg`, `MANIFEST.in` and `Pipfile`.

```toml
[tool.poetry]
name = "my-package"
version = "0.1.0"
description = "The description of the package"

license = "MIT"

authors = [
    "Sébastien Eustace <sebastien@eustace.io>"
]

readme = "README.md"

repository = "https://github.com/python-poetry/poetry"
homepage = "https://python-poetry.org"

keywords = ["packaging", "poetry"]

[tool.poetry.dependencies]
python = "^3.8"  # Compatible python versions must be declared here
aiohttp = "^3.8.1"
# Dependencies with extras
requests = { version = "^2.28", extras = [ "security" ] }
# Python specific dependencies with prereleases allowed
tomli = { version = "^2.0.1", python = "<3.11", allow-prereleases = true }
# Git dependencies
cleo = { git = "https://github.com/python-poetry/cleo.git", branch = "master" }

# Optional dependencies (extras)
pendulum = { version = "^2.1.2", optional = true }

[tool.poetry.dev-dependencies]
pytest = "^7.1.2"
pytest-cov = "^3.0"

[tool.poetry.scripts]
my-script = "my_package:main"
```

There are some things we can notice here:

* It will try to enforce [semantic versioning](<http://semver.org>) as the best practice in version naming.
* You can specify the readme, included and excluded files: no more `MANIFEST.in`.
`poetry` will also use VCS ignore files (like `.gitignore`) to populate the `exclude` section.
* Keywords can be specified and will act as tags on the packaging site.
* The dependencies sections support caret, tilde, wildcard, inequality and multiple requirements.
* You must specify the python versions for which your package is compatible.

`poetry` will also detect if you are inside a virtualenv and install the packages accordingly.
So, `poetry` can be installed globally and used everywhere.

`poetry` also comes with a full fledged dependency resolution library.

## Why?

Packaging systems and dependency management in Python are rather convoluted and hard to understand for newcomers.
Even for seasoned developers it might be cumbersome at times to create all files needed in a Python project: `setup.py`,
`requirements.txt`, `setup.cfg`, `MANIFEST.in` and `Pipfile`.

So I wanted a tool that would limit everything to a single configuration file to do:
dependency management, packaging and publishing.

It takes inspiration in tools that exist in other languages, like `composer` (PHP) or `cargo` (Rust).

And, finally, I started `poetry` to bring another exhaustive dependency resolver to the Python community apart from
[Conda's](https://conda.io).

## Resources

* [Official Website](https://python-poetry.org)
* [Issue Tracker](https://github.com/python-poetry/poetry/issues)
* [Discord](https://discord.com/invite/awxPgve)
