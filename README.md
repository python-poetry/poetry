# Poetry: Dependency Management for Python

Poetry helps you declare, manage and install dependencies of Python projects,
ensuring you have the right stack everywhere.

![Poetry Install](https://raw.githubusercontent.com/python-poetry/poetry/master/assets/install.gif)

It supports Python 3.7+.


[![Tests Status](https://github.com/python-poetry/poetry/workflows/Tests/badge.svg?branch=master&event=push)](https://github.com/python-poetry/poetry/actions?query=workflow%3ATests+branch%3Amaster+event%3Apush)
[![Stable Version](https://img.shields.io/pypi/v/poetry?label=stable)](https://pypi.org/project/poetry/)
[![Pre-release Version](https://img.shields.io/github/v/release/python-poetry/poetry?label=alpha&include_prereleases&sort=semver)](https://pypi.org/project/poetry/#history)
[![Downloads](https://img.shields.io/pypi/dm/poetry)](https://pypistats.org/packages/poetry)
[![Discord](https://img.shields.io/discord/487711540787675139?logo=discord)](https://discord.com/invite/awxPgve)

The [complete documentation](https://python-poetry.org/docs/) is available on the [official website](https://python-poetry.org).

## Installation

Instructions on how to install `poetry` can be found [here](https://python-poetry.org/docs/master/#installation).
You can also refer [here](https://python-poetry.org/docs/master/#enable-tab-completion-for-bash-fish-or-zsh) for
information on how to enable tab completion in your environment.

## Introduction

`poetry` is a tool to handle dependency installation as well as building and packaging of Python packages.
It only needs one file to do all of that: the new, [standardized](https://www.python.org/dev/peps/pep-0518/) `pyproject.toml`.

In other words, poetry uses `pyproject.toml` to replace `setup.py`, `requirements.txt`, `setup.cfg`, `MANIFEST.in` and the newly added `Pipfile`.

```toml
[tool.poetry]
name = "my-package"
version = "0.1.0"
description = "The description of the package"

license = "MIT"

authors = [
    "Sébastien Eustace <sebastien@eustace.io>"
]

readme = "README.md"  # Markdown files are supported

repository = "https://github.com/python-poetry/poetry"
homepage = "https://github.com/python-poetry/poetry"

keywords = ["packaging", "poetry"]

[tool.poetry.dependencies]
python = "~2.7 || ^3.2"  # Compatible python versions must be declared here
toml = "^0.9"
# Dependencies with extras
requests = { version = "^2.13", extras = [ "security" ] }
# Python specific dependencies with prereleases allowed
pathlib2 = { version = "^2.2", python = "~2.7", allow-prereleases = true }
# Git dependencies
cleo = { git = "https://github.com/sdispater/cleo.git", branch = "master" }

# Optional dependencies (extras)
pendulum = { version = "^1.4", optional = true }

[tool.poetry.dev-dependencies]
pytest = "^3.0"
pytest-cov = "^2.4"

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
`requirements.txt`, `setup.cfg`, `MANIFEST.in` and the newly added `Pipfile`.

So I wanted a tool that would limit everything to a single configuration file to do:
dependency management, packaging and publishing.

It takes inspiration in tools that exist in other languages, like `composer` (PHP) or `cargo` (Rust).

And, finally, I started `poetry` to bring another exhaustive dependency resolver to the Python community apart from
[Conda's](https://conda.io).

### What about Pipenv?

In short: I do not like the CLI it provides, or some of the decisions made,
and I think we can make a better and more intuitive one. Here are a few things
that I don't like.

#### Dependency resolution

The dependency resolution is erratic and will fail even if there is a solution. Let's take an example:

```bash
pipenv install oslo.utils==1.4.0
```

will fail with this error:

```text
Could not find a version that matches pbr!=0.7,!=2.1.0,<1.0,>=0.6,>=2.0.0
```

while Poetry will get you the right set of packages:

```bash
poetry add oslo.utils=1.4.0
```

results in :

```text
  - Installing pytz (2018.3)
  - Installing netifaces (0.10.6)
  - Installing netaddr (0.7.19)
  - Installing oslo.i18n (2.1.0)
  - Installing iso8601 (0.1.12)
  - Installing six (1.11.0)
  - Installing babel (2.5.3)
  - Installing pbr (0.11.1)
  - Installing oslo.utils (1.4.0)
```

This is possible thanks to the efficient dependency resolver at the heart of Poetry.

Here is a breakdown of what exactly happens here:

`oslo.utils (1.4.0)` depends on:

- `pbr (>=0.6,!=0.7,<1.0)`
- `Babel (>=1.3)`
- `six (>=1.9.0)`
- `iso8601 (>=0.1.9)`
- `oslo.i18n (>=1.3.0)`
- `netaddr (>=0.7.12)`
- `netifaces (>=0.10.4)`

What interests us is `pbr (>=0.6,!=0.7,<1.0)`.

At this point, poetry will choose `pbr==0.11.1` which is the latest version that matches the constraint.

Next it will try to select `oslo.i18n==3.20.0` which is the latest version that matches `oslo.i18n (>=1.3.0)`.

However this version requires `pbr (!=2.1.0,>=2.0.0)` which is incompatible with `pbr==0.11.1`,
so `poetry` will try to find a version of `oslo.i18n` that satisfies `pbr (>=0.6,!=0.7,<1.0)`.

By analyzing the releases of `oslo.i18n`, it will find `oslo.i18n==2.1.0` which requires `pbr (>=0.11,<2.0)`.
At this point the rest of the resolution is straightforward since there is no more conflict.

## Resources

* [Official Website](https://python-poetry.org)
* [Issue Tracker](https://github.com/python-poetry/poetry/issues)
* [Discord](https://discord.com/invite/awxPgve)
