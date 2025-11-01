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
Poetry offers a lockfile to ensure repeatable installs, and can build your project for distribution.


## System requirements

Poetry requires **Python 3.9+**. It is multi-platform and the goal is to make it work equally well
on Linux, macOS and Windows.

## Installation

{{% note %}}
If you are viewing documentation for the development branch, you may wish to install a preview or development version of Poetry.
See the **advanced** installation instructions to use a preview or alternate version of Poetry.
{{% /note %}}

{{< tabs tabTotal="4" tabID1="installing-with-pipx" tabID2="installing-with-the-official-installer" tabID3="installing-manually" tabID4="ci-recommendations" tabName1="With pipx" tabName2="With the official installer" tabName3="Manually (advanced)" tabName4="CI recommendations">}}

{{< tab tabID="installing-with-pipx" >}}

[`pipx`](https://github.com/pypa/pipx) is used to install Python CLI applications globally while still isolating them in virtual environments.
`pipx` will manage upgrades and uninstalls when used to install Poetry.

{{< steps >}}
{{< step >}}
**Install pipx**

If `pipx` is not already installed, you can follow any of the options in the
[official pipx installation instructions](https://pipx.pypa.io/stable/installation/).
Any non-ancient version of `pipx` will do.

{{< /step >}}
{{< step >}}
**Install Poetry**

```bash
pipx install poetry
```
{{< /step >}}
{{< step >}}
**Install Poetry (advanced)**

{{% note %}}
You can skip this step, if you simply want the latest version and already installed Poetry as described in the
previous step. This step details advanced usages of this installation method. For example, installing Poetry from
source, having multiple versions installed at the same time etc.
{{% /note %}}

`pipx` can install different versions of Poetry, using the same syntax as pip:

```bash
pipx install poetry==1.8.4
```

`pipx` can also install versions of Poetry in parallel, which allows for easy testing of alternate or prerelease
versions. Each version is given a unique, user-specified suffix, which will be used to create a unique binary name:

```bash
pipx install --suffix=@1.8.4 poetry==1.8.4
poetry@1.8.4 --version
```

```bash
pipx install --suffix=@preview --pip-args=--pre poetry
poetry@preview --version
```

Finally, `pipx` can install any valid [pip requirement spec](https://pip.pypa.io/en/stable/cli/pip_install/), which
allows for installations of the development version from `git`, or even for local testing of pull requests:

```bash
pipx install --suffix @main git+https://github.com/python-poetry/poetry.git@main
pipx install --suffix @pr1234 git+https://github.com/python-poetry/poetry.git@refs/pull/1234/head
```

{{< /step >}}
{{< step >}}
**Update Poetry**

```bash
pipx upgrade poetry
```
{{< /step >}}
{{< step >}}
**Uninstall Poetry**

```bash
pipx uninstall poetry
```
{{< /step >}}
{{< /steps >}}

{{< /tab >}}
{{< tab tabID="installing-with-the-official-installer" >}}

We provide a custom installer that will install Poetry in a new virtual environment
and allows Poetry to manage its own environment.

{{< steps >}}
{{< step >}}
**Install Poetry**

The installer script is available directly at [install.python-poetry.org](https://install.python-poetry.org),
and is developed in [its own repository](https://github.com/python-poetry/install.python-poetry.org).
The script can be executed directly (i.e. 'curl python') or downloaded and then executed from disk
(e.g. in a CI environment).

**Linux, macOS, Windows (WSL)**

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

**Windows (Powershell)**
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

{{% note %}}
If you have installed Python through the Microsoft Store, replace `py` with `python` in the command
above.
{{% /note %}}

{{< /step >}}
{{< step >}}
**Install Poetry (advanced)**

{{% note %}}
You can skip this step, if you simply want the latest version and already installed Poetry as described in the
previous step. This step details advanced usages of this installation method. For example, installing Poetry from
source, using a pre-release build, configuring a different installation location etc.
{{% /note %}}

By default, Poetry is installed into a platform and user-specific directory:

- `~/Library/Application Support/pypoetry` on macOS.
- `~/.local/share/pypoetry` on Linux/Unix.
- `%APPDATA%\pypoetry` on Windows.

If you wish to change this, you may define the `$POETRY_HOME` environment variable:

```bash
curl -sSL https://install.python-poetry.org | POETRY_HOME=/etc/poetry python3 -
```

If you want to install prerelease versions, you can do so by passing the `--preview` option to the installation script
or by using the `$POETRY_PREVIEW` environment variable:

```bash
curl -sSL https://install.python-poetry.org | python3 - --preview
curl -sSL https://install.python-poetry.org | POETRY_PREVIEW=1 python3 -
```

Similarly, if you want to install a specific version, you can use `--version` option or the `$POETRY_VERSION`
environment variable:

```bash
curl -sSL https://install.python-poetry.org | python3 - --version 1.8.4
curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.8.4 python3 -
```

You can also install Poetry from a `git` repository by using the `--git` option:

```bash
curl -sSL https://install.python-poetry.org | python3 - --git https://github.com/python-poetry/poetry.git@main
````
If you want to install different versions of Poetry in parallel, a good approach is the installation with pipx and suffix.

{{< /step >}}
{{< step >}}
**Add Poetry to your PATH**

The installer creates a `poetry` wrapper in a well-known, platform-specific directory:

- `$HOME/.local/bin` on Linux/Unix.
- `%APPDATA%\Python\Scripts` on Windows.
- `$POETRY_HOME/bin` if `$POETRY_HOME` is set.

If this directory is not present in your `$PATH`, you can add it in order to invoke Poetry
as `poetry`.

Alternatively, the full path to the `poetry` binary can always be used:

- `~/Library/Application Support/pypoetry/venv/bin/poetry` on macOS.
- `~/.local/share/pypoetry/venv/bin/poetry` on Linux/Unix.
- `%APPDATA%\pypoetry\venv\Scripts\poetry` on Windows.
- `$POETRY_HOME/venv/bin/poetry` if `$POETRY_HOME` is set.

{{< /step >}}
{{< step >}}
**Use Poetry**

Once Poetry is installed and in your `$PATH`, you can execute the following:

```bash
poetry --version
```

If you see something like `Poetry (version 2.0.0)`, your installation is ready to use!
{{< /step >}}
{{< step >}}
**Update Poetry**

Poetry is able to update itself when installed using the official installer.

{{% warning %}}
Especially on Windows, `self update` may be problematic
so that a re-install with the installer should be preferred.
{{% /warning %}}

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
poetry self update 1.8.4
```

{{< /step >}}
{{< step >}}
**Uninstall Poetry**

If you decide Poetry isn't your thing, you can completely remove it from your system
by running the installer again with the `--uninstall` option or by setting
the `POETRY_UNINSTALL` environment variable before executing the installer.

```bash
curl -sSL https://install.python-poetry.org | python3 - --uninstall
curl -sSL https://install.python-poetry.org | POETRY_UNINSTALL=1 python3 -
```
{{< /step >}}
{{< /steps >}}

{{< /tab >}}
{{< tab tabID="installing-manually" >}}

Poetry can be installed manually using `pip` and the `venv` module. By doing so you will essentially perform the steps carried
out by the official installer. As this is an advanced installation method, these instructions are Unix-only and omit specific
examples such as installing from `git`.

The variable `$VENV_PATH` will be used to indicate the path at which the virtual environment was created.

```bash
python3 -m venv $VENV_PATH
$VENV_PATH/bin/pip install -U pip setuptools
$VENV_PATH/bin/pip install poetry
```

Poetry will be available at `$VENV_PATH/bin/poetry` and can be invoked directly or symlinked elsewhere.

To uninstall Poetry, simply delete the entire `$VENV_PATH` directory.

{{< /tab >}}
{{< tab tabID="ci-recommendations" >}}
Unlike development environments, where making use of the latest tools is desirable, in a CI environment reproducibility
should be made the priority. Here are some suggestions for installing Poetry in such an environment.

**Version pinning**

Whatever method you use, it is highly recommended to explicitly control the version of Poetry used, so that you are able
to upgrade after performing your own validation. Each install method has a different syntax for setting the version that
is used in the following examples.

**Using pipx**

Just as `pipx` is a powerful tool for development use, it is equally useful in a CI environment
and should be one of your top choices for use of Poetry in CI.

```bash
pipx install poetry==2.0.0
```

**Using install.python-poetry.org**

{{% note %}}
The official installer script ([install.python-poetry.org](https://install.python-poetry.org)) offers a streamlined and
simplified installation of Poetry, sufficient for developer use or for simple pipelines. However, in a CI environment
the other two supported installation methods (pipx and manual) should be seriously considered.
{{% /note %}}

Downloading a copy of the installer script to a place accessible by your CI pipelines (or maintaining a copy of the
[repository](https://github.com/python-poetry/install.python-poetry.org)) is strongly suggested, to ensure your
pipeline's stability and to maintain control over what code is executed.

By default, the installer will install to a user-specific directory. In more complex pipelines that may make accessing
Poetry difficult (especially in cases like multi-stage container builds). It is highly suggested to make use of
`$POETRY_HOME` when using the official installer in CI, as that way the exact paths can be controlled.

```bash
export POETRY_HOME=/opt/poetry
python3 install-poetry.py --version 2.0.0
$POETRY_HOME/bin/poetry --version
```

**Using pip (aka manually)**

For maximum control in your CI environment, installation with `pip` is fully supported and something you should
consider. While this requires more explicit commands and knowledge of Python packaging from you, it in return offers the
best debugging experience, and leaves you subject to the fewest external tools.

```bash
export POETRY_HOME=/opt/poetry
python3 -m venv $POETRY_HOME
$POETRY_HOME/bin/pip install poetry==2.0.0
$POETRY_HOME/bin/poetry --version
```

{{% note %}}
If you install Poetry via `pip`, ensure you have Poetry installed into an isolated environment that is **not the same**
as the target environment managed by Poetry. If Poetry and your project are installed into the same environment, Poetry
is likely to upgrade or uninstall its own dependencies (causing hard-to-debug and understand errors).
{{% /note %}}

{{< /tab >}}
{{< /tabs >}}

{{% warning %}}
Poetry should always be installed in a dedicated virtual environment to isolate it from the rest of your system.
Each of the above described installation methods ensures that.
It should in no case be installed in the environment of the project that is to be managed by Poetry.
This ensures that Poetry's own dependencies will not be accidentally upgraded or uninstalled.
In addition, the isolated virtual environment in which poetry is installed should not be activated for running poetry commands.
{{% /warning %}}

## Enable tab completion for Bash, Fish, or Zsh

`poetry` supports generating completion scripts for Bash, Fish, and Zsh.

{{% note %}}
You may need to restart your shell in order for these changes to take effect.
{{% /note %}}

See `poetry help completions` for full details, but the gist is as simple as using one of the following:

### Bash

#### Auto-loaded (recommended)

```bash
poetry completions bash >> ~/.bash_completion
```

#### Lazy-loaded

```bash
poetry completions bash > ${XDG_DATA_HOME:-~/.local/share}/bash-completion/completions/poetry
```

### Fish

```fish
poetry completions fish > ~/.config/fish/completions/poetry.fish
```

### Zsh

```zsh
poetry completions zsh > ~/.zfunc/_poetry
```

You must then add the following lines in your `~/.zshrc`, if they do not already exist:

```bash
fpath+=~/.zfunc
autoload -Uz compinit && compinit
```

#### Oh My Zsh

```zsh
mkdir $ZSH_CUSTOM/plugins/poetry
poetry completions zsh > $ZSH_CUSTOM/plugins/poetry/_poetry
```
You must then add `poetry` to your plugins array in `~/.zshrc`:

```text
plugins(
	poetry
	...
	)
```

#### Prezto

```zsh
poetry completions zsh > ~/.zprezto/modules/completion/external/src/_poetry
```

If completions still don't work, try removing `~/.cache/prezto/zcompcache` and starting a new shell.
