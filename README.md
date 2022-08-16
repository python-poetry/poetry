# Poetry: Dependency Management for Python

Poetry helps you declare, manage and install dependencies of Python projects,
ensuring you have the right stack everywhere.

![Poetry Install](https://raw.githubusercontent.com/python-poetry/poetry/master/assets/install.gif)

It supports Python 2.7 and 3.5+.

**Note**: Python 2.7 and 3.5 will no longer be supported in the next feature release (1.2).
You should consider updating your Python version to a supported one.

[![Tests Status](https://github.com/python-poetry/poetry/workflows/Tests/badge.svg?branch=master&event=push)](https://github.com/python-poetry/poetry/actions?query=workflow%3ATests+branch%3Amaster+event%3Apush)

The [complete documentation](https://python-poetry.org/docs/) is available on the [official website](https://python-poetry.org).

## Installation

Poetry provides a custom installer that will install `poetry` isolated
from the rest of your system by vendorizing its dependencies. This is the
recommended way of installing `poetry`.

```bash
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
```

Alternatively, you can download the `get-poetry.py` file and execute it separately.

The setup script must be able to find one of following executables in your shell's path environment:

- `python` (which can be a py3 or py2 interpreter)
- `python3`
- `py.exe -3` (Windows)
- `py.exe -2` (Windows)

If you want to install prerelease versions, you can do so by passing `--preview` to `get-poetry.py`:

```bash
python get-poetry.py --preview
```

Similarly, if you want to install a specific version, you can use `--version`:

```bash
python get-poetry.py --version 0.7.0
```

Using `pip` to install `poetry` is also possible.

```bash
pip install --user poetry
```

Be aware, however, that it will also install poetry's dependencies
which might cause conflicts.

## Updating `poetry`

Updating poetry to the latest stable version is as simple as calling the `self update` command.

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
poetry self update 1.0.0
```

*Note:*

    If you are still on poetry version < 1.0 use `poetry self:update` instead.


## Enable tab completion for Bash, Fish, or Zsh

`poetry` supports generating completion scripts for Bash, Fish, and Zsh.
See `poetry help completions` for full details, but the gist is as simple as using one of the following:

```bash
# Bash
poetry completions bash > /etc/bash_completion.d/poetry.bash-completion

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
mkdir $ZSH/plugins/poetry
poetry completions zsh > $ZSH/plugins/poetry/_poetry

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

readme = 'README.md'  # Markdown files are supported

repository = "https://github.com/python-poetry/poetry"
homepage = "https://github.com/python-poetry/poetry"

keywords = ['packaging', 'poetry']

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
my-script = 'my_package:main'
```

There are some things we can notice here:

* It will try to enforce [semantic versioning](<http://semver.org>) as the best practice in version naming.
* You can specify the readme, included and excluded files: no more `MANIFEST.in`.
`poetry` will also use VCS ignore files (like `.gitignore`) to populate the `exclude` section.
* Keywords (up to 5) can be specified and will act as tags on the packaging site.
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

And, finally, there is no reliable tool to properly resolve dependencies in Python, so I started `poetry`
to bring an exhaustive dependency resolver to the Python community.

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
* [Discord](https://discordapp.com/invite/awxPgve)
