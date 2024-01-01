---
title: "Managing environments"
draft: false
type: docs
layout: "docs"

menu:
  docs:
    weight: 60
---

# Managing environments

Poetry makes project environment isolation one of its core features.

What this means is that it will always work isolated from your global Python installation.
To achieve this, it will first check if it's currently running inside a virtual environment.
If it is, it will use it directly without creating a new one. But if it's not, it will use
one that it has already created or create a brand new one for you.

By default, Poetry will try to use the Python version used during Poetry's installation
to create the virtual environment for the current project.

However, for various reasons, this Python version might not be compatible
with the `python` range supported by the project. In this case, Poetry will try
to find one that is and use it. If it's unable to do so then you will be prompted
to activate one explicitly, see [Switching environments](#switching-between-environments).

{{% note %}}
If you use a tool like [pyenv](https://github.com/pyenv/pyenv) to manage different Python versions,
you can set the experimental `virtualenvs.prefer-active-python` option to `true`. Poetry
will then try to find the current `python` of your shell.

For instance, if your project requires a newer Python than is available with
your system, a standard workflow would be:

```bash
pyenv install 3.9.8
pyenv local 3.9.8  # Activate Python 3.9 for the current project
poetry install
```

{{% /note %}}

{{% note %}}
Since version 1.2, Poetry no longer supports managing environments for Python 2.7.
{{% /note %}}

## Switching between environments

Sometimes this might not be feasible for your system, especially Windows where `pyenv`
is not available, or you simply prefer to have a more explicit control over your environment.
For this specific purpose, you can use the `env use` command to tell Poetry
which Python version to use for the current project.

```bash
poetry env use /full/path/to/python
```

If you have the python executable in your `PATH` you can use it:

```bash
poetry env use python3.7
```

You can even just use the minor Python version in this case:

```bash
poetry env use 3.7
```

If you want to disable the explicitly activated virtual environment, you can use the
special `system` Python version to retrieve the default behavior:

```bash
poetry env use system
```

## Displaying the environment information

If you want to get basic information about the currently activated virtual environment,
you can use the `env info` command:

```bash
poetry env info
```

will output something similar to this:

```text
Virtualenv
Python:         3.7.1
Implementation: CPython
Path:           /path/to/poetry/cache/virtualenvs/test-O3eWbxRl-py3.7
Valid:          True

Base
Platform: darwin
OS:       posix
Python:   /path/to/main/python
```

If you only want to know the path to the virtual environment, you can pass the `--path` option
to `env info`:

```bash
poetry env info --path
```

If you only want to know the path to the python executable (useful for running mypy from a global environment without installing it in the virtual environment), you can pass the `--executable` option
to `env info`:

```bash
poetry env info --executable
```

## Listing the environments associated with the project

You can also list all the virtual environments associated with the current project
with the `env list` command:

```bash
poetry env list
```

will output something like the following:

```text
test-O3eWbxRl-py3.6
test-O3eWbxRl-py3.7 (Activated)
```

You can pass the option `--full-path` to display the full path to the environments:

```bash
poetry env list --full-path
```

## Deleting the environments

Finally, you can delete existing virtual environments by using `env remove`:

```bash
poetry env remove /full/path/to/python
poetry env remove python3.7
poetry env remove 3.7
poetry env remove test-O3eWbxRl-py3.7
```

You can delete more than one environment at a time.

```bash
poetry env remove python3.6 python3.7 python3.8
```

Use the `--all` option to delete all virtual environments at once.

```bash
poetry env remove --all
```

If you remove the currently activated virtual environment, it will be automatically deactivated.
