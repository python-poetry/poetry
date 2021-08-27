# Poetry: Dependency Management for Python

Poetry helps you declare, manage and install dependencies of Python projects,
ensuring you have the right stack everywhere.

![Poetry Install](https://raw.githubusercontent.com/python-poetry/poetry/master/assets/install.gif)

<<<<<<< HEAD
It supports Python 3.6+.


[![Tests Status](https://github.com/python-poetry/poetry/workflows/Tests/badge.svg?branch=master&event=push)](https://github.com/python-poetry/poetry/actions?query=workflow%3ATests+branch%3Amaster+event%3Apush)
[![Stable Version](https://img.shields.io/pypi/v/poetry?label=stable)](https://pypi.org/project/poetry/)
[![Pre-release Version](https://img.shields.io/github/v/release/python-poetry/poetry?label=alpha&include_prereleases&sort=semver)](https://pypi.org/project/poetry/#history)
[![Downloads](https://img.shields.io/pypi/dm/poetry)](https://pypistats.org/packages/poetry)
[![Discord](https://img.shields.io/discord/487711540787675139?logo=discord)](https://discord.com/invite/awxPgve)
=======
It supports Python 2.7 and 3.5+.

**Note**: Python 2.7 and 3.5 will no longer be supported in the next feature release (1.2).
You should consider updating your Python version to a supported one.

[![Tests Status](https://github.com/python-poetry/poetry/workflows/Tests/badge.svg?branch=master&event=push)](https://github.com/python-poetry/poetry/actions?query=workflow%3ATests+branch%3Amaster+event%3Apush)
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

The [complete documentation](https://python-poetry.org/docs/) is available on the [official website](https://python-poetry.org).

## Installation

Poetry provides a custom installer that will install `poetry` isolated
from the rest of your system.

### osx / linux / bashonwindows install instructions
```bash
<<<<<<< HEAD
curl -sSL https://install.python-poetry.org | python3 -
```
### windows powershell install instructions
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
=======
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python -
```
### windows powershell install instructions
```powershell
(Invoke-WebRequest -Uri https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py -UseBasicParsing).Content | python -
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
```

**Warning**: The previous `get-poetry.py` installer is now deprecated, if you are currently using it
you should migrate to the new, supported, `install-poetry.py` installer.

The installer installs the `poetry` tool to Poetry's `bin` directory. This location depends on your system:

- `$HOME/.local/bin` for Unix
- `%APPDATA%\Python\Scripts` on Windows

If this directory is not on your `PATH`, you will need to add it manually
if you want to invoke Poetry with simply `poetry`.

Alternatively, you can use the full path to `poetry` to use it.

Once Poetry is installed you can execute the following:

```bash
poetry --version
```

If you see something like `Poetry (version 1.2.0)` then you are ready to use Poetry.
If you decide Poetry isn't your thing, you can completely remove it from your system
by running the installer again with the `--uninstall` option or by setting
the `POETRY_UNINSTALL` environment variable before executing the installer.

```bash
<<<<<<< HEAD
curl -sSL https://install.python-poetry.org | python3 - --uninstall
curl -sSL https://install.python-poetry.org | POETRY_UNINSTALL=1 python3 -
=======
python install-poetry.py --uninstall
POETRY_UNINSTALL=1 python install-poetry.py
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
```

By default, Poetry is installed into the user's platform-specific home directory.
If you wish to change this, you may define the `POETRY_HOME` environment variable:

```bash
<<<<<<< HEAD
curl -sSL https://install.python-poetry.org | POETRY_HOME=/etc/poetry python3 -
=======
POETRY_HOME=/etc/poetry python install-poetry.py
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
```

If you want to install prerelease versions, you can do so by passing `--preview` option to `install-poetry.py`
or by using the `POETRY_PREVIEW` environment variable:

```bash
<<<<<<< HEAD
curl -sSL https://install.python-poetry.org | python3 - --preview
curl -sSL https://install.python-poetry.org | POETRY_PREVIEW=1 python3 -
=======
python install-poetry.py --preview
POETRY_PREVIEW=1 python install-poetry.py
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
```

Similarly, if you want to install a specific version, you can use `--version` option or the `POETRY_VERSION`
environment variable:

```bash
<<<<<<< HEAD
curl -sSL https://install.python-poetry.org | python3 - --version 1.2.0
curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.2.0 python3 -
=======
python install-poetry.py --version 1.2.0
POETRY_VERSION=1.2.0 python install-poetry.py
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
```

You can also install Poetry for a `git` repository by using the `--git` option:

```bash
<<<<<<< HEAD
curl -sSL https://install.python-poetry.org | python3 - --git https://github.com/python-poetry/poetry.git@master
````

_Note that the installer does not support Python < 3.6._
=======
python install-poetry.py --git https://github.com/python-poetry/poetry.git@master
````

**Note**: Note that the installer does not support Python < 3.6.
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

## Updating `poetry`

Updating poetry to the latest stable version is as simple as calling the `self update` command.

**Warning**: Poetry versions installed using the now deprecated `get-poetry.py` installer will not be able to use this
command to update to 1.2 releases or later. Migrate to using the `install-poetry.py` installer or `pipx`.

```bash
poetry self update
```

If you want to install prerelease versions, you can use the `--preview` option.

```bash
poetry self update --preview
```

And finally, if you want to install a specific version you can pass it as an argument
to `self update`.

```bash
poetry self update 1.2.0
```


## Enable tab completion for Bash, Fish, or Zsh

`poetry` supports generating completion scripts for Bash, Fish, and Zsh.
See `poetry help completions` for full details, but the gist is as simple as using one of the following:

```bash
# Bash
poetry completions bash > /etc/bash_completion.d/poetry.bash-completion

<<<<<<< HEAD
# Fish
poetry completions fish > ~/.config/fish/completions/poetry.fish

# Zsh
poetry completions zsh > ~/.zfunc/_poetry

# Zsh (Oh-My-Zsh)
mkdir $ZSH_CUSTOM/plugins/poetry
poetry completions zsh > $ZSH_CUSTOM/plugins/poetry/_poetry
rm ~/.zcompdump*
# add `poetry` in the `plugins` list (https://github.com/ohmyzsh/ohmyzsh#enabling-plugins)
=======
# Bash (Homebrew)
poetry completions bash > $(brew --prefix)/etc/bash_completion.d/poetry.bash-completion

# Fish
poetry completions fish > ~/.config/fish/completions/poetry.fish

# Fish (Homebrew)
poetry completions fish > (brew --prefix)/share/fish/vendor_completions.d/poetry.fish

# Zsh
poetry completions zsh > ~/.zfunc/_poetry

# Zsh (Homebrew)
poetry completions zsh > $(brew --prefix)/share/zsh/site-functions/_poetry

# Zsh (Oh-My-Zsh)
mkdir $ZSH_CUSTOM/plugins/poetry
poetry completions zsh > $ZSH_CUSTOM/plugins/poetry/_poetry
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

# Zsh (prezto)
poetry completions zsh > ~/.zprezto/modules/completion/external/src/_poetry
```

*Note:* you may need to restart your shell in order for the changes to take
effect.

For `zsh`, you must then add the following line in your `~/.zshrc` before
`compinit` (not for homebrew setup):

```zsh
fpath+=~/.zfunc
```


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

<<<<<<< HEAD
readme = "README.md"  # Markdown files are supported
=======
readme = 'README.md'  # Markdown files are supported
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

repository = "https://github.com/python-poetry/poetry"
homepage = "https://github.com/python-poetry/poetry"

<<<<<<< HEAD
keywords = ["packaging", "poetry"]
=======
keywords = ['packaging', 'poetry']
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)

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
<<<<<<< HEAD
my-script = "my_package:main"
=======
my-script = 'my_package:main'
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
```

There are some things we can notice here:

* It will try to enforce [semantic versioning](<http://semver.org>) as the best practice in version naming.
* You can specify the readme, included and excluded files: no more `MANIFEST.in`.
`poetry` will also use VCS ignore files (like `.gitignore`) to populate the `exclude` section.
<<<<<<< HEAD
* Keywords can be specified and will act as tags on the packaging site.
=======
* Keywords (up to 5) can be specified and will act as tags on the packaging site.
>>>>>>> d7cf7a8e (Fix `remove` command to handle `.venv` dirs)
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
