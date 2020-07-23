# Introduction

Poetry is a tool for dependency management and packaging in Python.
It allows you to declare the libraries your project depends on and it will manage (install/update) them for you.


## System requirements

Poetry requires Python 2.7 or 3.5+. It is multi-platform and the goal is to make it work equally well
on Windows, Linux and OSX.

!!! note

    Python 2.7 and 3.5 will no longer be supported in the next feature release (1.2).
    You should consider updating your Python version to a supported one.


## Installation

Poetry provides a custom installer that will install `poetry` isolated
from the rest of your system by vendorizing its dependencies. This is the
recommended way of installing `poetry`.

### osx / linux / bashonwindows install instructions
```bash
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
```
### windows powershell install instructions
```powershell
(Invoke-WebRequest -Uri https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py -UseBasicParsing).Content | python
```

!!! note

    You only need to install Poetry once. It will automatically pick up the current
    Python version and use it to [create virtualenvs](/docs/managing-environments) accordingly.

The installer installs the `poetry` tool to Poetry's `bin` directory.
On Unix it is located at `$HOME/.poetry/bin` and on Windows at `%USERPROFILE%\.poetry\bin`.

This directory will be in your `$PATH` environment variable,
which means you can run them from the shell without further configuration.
Open a new shell and type the following:

```bash
poetry --version
```

If you see something like `Poetry 0.12.0` then you are ready to use Poetry.
If you decide Poetry isn't your thing, you can completely remove it from your system
by running the installer again with the `--uninstall` option or by setting
the `POETRY_UNINSTALL` environment variable before executing the installer.

```bash
python get-poetry.py --uninstall
POETRY_UNINSTALL=1 python get-poetry.py
```

By default, Poetry is installed into the user's platform-specific home directory. If you wish to change this, you may define the `POETRY_HOME` environment variable:

```bash
POETRY_HOME=/etc/poetry python get-poetry.py
```

If you want to install prerelease versions, you can do so by passing `--preview` to `get-poetry.py`
or by using the `POETRY_PREVIEW` environment variable:

```bash
python get-poetry.py --preview
POETRY_PREVIEW=1 python get-poetry.py
```

Similarly, if you want to install a specific version, you can use `--version` or the `POETRY_VERSION`
environment variable:

```bash
python get-poetry.py --version 0.12.0
POETRY_VERSION=0.12.0 python get-poetry.py
```

!!!note

    Note that the installer does not support Poetry releases < 0.12.0.

!!!note

    The setup script must be able to find one of following executables in your shell's path environment:

    - `python` (which can be a py3 or py2 interpreter)
    - `python3`
    - `py.exe -3` (Windows)
    - `py.exe -2` (Windows)

### Alternative installation methods (not recommended)

!!!note

    Using alternative installation methods will make Poetry always
    use the Python version for which it has been installed to create
    virtualenvs.

    So, you will need to install Poetry for each Python version you
    want to use and switch between them.

#### Installing with `pip`

Using `pip` to install Poetry is possible.

```bash
pip install --user poetry
```

!!!warning

    Be aware that it will also install Poetry's dependencies
    which might cause conflicts with other packages.

#### Installing with `pipx`

Using [`pipx`](https://github.com/cs01/pipx) to install Poetry is also possible. [pipx] is used to install Python CLI applications globally while still isolating them in virtual environments. This allows for clean upgrades and uninstalls. pipx supports Python 3.6 and later. If using an earlier version of Python, consider [pipsi](https://github.com/mitsuhiko/pipsi).

```bash
pipx install poetry
```

```bash
pipx upgrade poetry
```

```bash
pipx uninstall poetry
```

[Github repository](https://github.com/cs01/pipx).


## Updating `poetry`

Updating Poetry to the latest stable version is as simple as calling the `self update` command.

```bash
poetry self update
```

If you want to install pre-release versions, you can use the `--preview` option.

```bash
poetry self update --preview
```

And finally, if you want to install a specific version, you can pass it as an argument
to `self update`.

```bash
poetry self update 0.8.0
```

!!!note

    The `self update` command will only work if you used the recommended
    installer to install Poetry.

!!!note

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

# Oh-My-Zsh
mkdir $ZSH/plugins/poetry
poetry completions zsh > $ZSH/plugins/poetry/_poetry

# prezto
poetry completions zsh > ~/.zprezto/modules/completion/external/src/_poetry

```

!!! note

    You may need to restart your shell in order for the changes to take effect.

For `zsh`, you must then add the following line in your `~/.zshrc` before `compinit`:

```bash
fpath+=~/.zfunc
```

For `oh-my-zsh`, you must then enable poetry in your `~/.zshrc` plugins

```
plugins(
	poetry
	...
	)
```
