---
title: "Introduction"
draft: false
type: docs
layout: "single"

menu:
  docs:
    weight: 0
---

# Introduction

Poetry is a tool for **dependency management** and **packaging** in Python.
It allows you to declare the libraries your project depends on and it will manage (install/update) them for you.


## System requirements

Poetry requires Python 3.6+. It is multi-platform and the goal is to make it work equally well
on Windows, Linux and OSX.


## Installation

Poetry provides a custom installer that will install `poetry` isolated
from the rest of your system.

### osx / linux / bashonwindows install instructions
```bash
curl -sSL https://install.python-poetry.org | python -
```
### windows powershell install instructions
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

{{% warning %}}
The previous `get-poetry.py` installer is now deprecated, if you are currently using it
you should migrate to the new, supported, `install-poetry.py` installer.
{{% /warning %}}

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
python install-poetry.py --uninstall
POETRY_UNINSTALL=1 python install-poetry.py
```

By default, Poetry is installed into the user's platform-specific home directory.
If you wish to change this, you may define the `POETRY_HOME` environment variable:

```bash
curl -sSL https://install.python-poetry.org | POETRY_HOME=/etc/poetry python -
```

If you want to install prerelease versions, you can do so by passing `--preview` option to `install-poetry.py`
or by using the `POETRY_PREVIEW` environment variable:

```bash
curl -sSL https://install.python-poetry.org | python - --preview
curl -sSL https://install.python-poetry.org | POETRY_PREVIEW=1 python -
```

Similarly, if you want to install a specific version, you can use `--version` option or the `POETRY_VERSION`
environment variable:

```bash
curl -sSL https://install.python-poetry.org | python - --version 1.2.0
curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.2.0 python -
```

You can also install Poetry for a `git` repository by using the `--git` option:

```bash
curl -sSL https://install.python-poetry.org | python - --git https://github.com/python-poetry/poetry.git@master
````

{{% note %}}
Note that the installer does not support Python < 3.6.
{{% /note %}}


### Alternative installation methods

#### Installing with `pipx`

Using [`pipx`](https://github.com/pipxproject/pipx) to install Poetry is also possible.
`pipx` is used to install Python CLI applications globally while still isolating them in virtual environments.
This allows for clean upgrades and uninstalls.

```bash
pipx install poetry
```

```bash
pipx upgrade poetry
```

```bash
pipx uninstall poetry
```


#### Installing with `pip`

Using `pip` to install Poetry is possible.

```bash
pip install --user poetry
```

{{% warning %}}
Be aware that it will also install Poetry's dependencies
which might cause conflicts with other packages.
{{% /warning %}}

## Updating `poetry`

Updating Poetry to the latest stable version is as simple as calling the `self update` command.

```bash
poetry self update
```

{{% warning %}}
Poetry versions installed using the now deprecated `get-poetry.py` installer will not be able to use this
command to update to 1.2 releases or later. Migrate to using the `install-poetry.py` installer or `pipx`.
{{% /warning %}}

If you want to install pre-release versions, you can use the `--preview` option.

```bash
poetry self update --preview
```

And finally, if you want to install a specific version, you can pass it as an argument
to `self update`.

```bash
poetry self update 1.2.0
```


## Enable tab completion for Bash, Fish, or Zsh

`poetry` supports generating completion scripts for Bash, Fish, and Zsh.
See `poetry help completions` for full details, but the gist is as simple as using one of the following:


```bash
# Bash
poetry completions bash > /etc/bash_completion.d/poetry

# Fish
poetry completions fish > ~/.config/fish/completions/poetry.fish

# Zsh
poetry completions zsh > ~/.zfunc/_poetry

# Oh-My-Zsh
mkdir $ZSH_CUSTOM/plugins/poetry
poetry completions zsh > $ZSH_CUSTOM/plugins/poetry/_poetry

# prezto
poetry completions zsh > ~/.zprezto/modules/completion/external/src/_poetry

```

{{% note %}}
You may need to restart your shell in order for the changes to take effect.
{{% /note %}}

For `zsh`, you must then add the following line in your `~/.zshrc` before `compinit`:

```bash
fpath+=~/.zfunc
```

For `oh-my-zsh`, you must then enable poetry in your `~/.zshrc` plugins

```text
plugins(
	poetry
	...
	)
```
