---
title: "Basic usage"
draft: false
type: docs
layout: single

menu:
  docs:
    weight: 10
---

# Basic usage

For the basic usage introduction we will be installing `pendulum`, a datetime library.
If you have not yet installed Poetry, refer to the [Introduction]({{< relref "docs" >}} "Introduction") chapter.

## Project setup

First, let's create our new project, let's call it `poetry-demo`:

```bash
poetry new poetry-demo
```

This will create the `poetry-demo` directory with the following content:

```text
poetry-demo
├── pyproject.toml
├── README.md
├── poetry_demo
│   └── __init__.py
└── tests
    └── __init__.py
```

The `pyproject.toml` file is what is the most important here. This will orchestrate
your project and its dependencies. For now, it looks like this:

```toml
[tool.poetry]
name = "poetry-demo"
version = "0.1.0"
description = ""
authors = ["Sébastien Eustace <sebastien@eustace.io>"]
readme = "README.md"
packages = [{include = "poetry_demo"}]

[tool.poetry.dependencies]
python = "^3.7"


[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

Poetry assumes your package contains a package with the same name as `tool.poetry.name`.
If this is not the case, populate `tool.poetry.packages` to specify your package or packages.

See [Packages](/docs/pyproject#packages) for more information.

### Initialising a pre-existing project

Instead of creating a new project, Poetry can be used to 'initialise' a pre-populated
directory. To interactively create a `pyproject.toml` file in directory `pre-existing-project`:

```bash
cd pre-existing-project
poetry init
```

### Specifying dependencies

If you want to add dependencies to your project, you can specify them in the `tool.poetry.dependencies` section.

```toml
[tool.poetry.dependencies]
pendulum = "^2.1"
```

As you can see, it takes a mapping of **package names** and **version constraints**.

Poetry uses this information to search for the right set of files in package "repositories" that you register
in the `tool.poetry.source` section, or on [PyPI](https://pypi.org) by default.

Also, instead of modifying the `pyproject.toml` file by hand, you can use the `add` command.

```bash
$ poetry add pendulum
```

It will automatically find a suitable version constraint **and install** the package and sub-dependencies.


## Using your virtual environment

By default, poetry creates a virtual environment in `{cache-dir}/virtualenvs` (`{cache-dir}\virtualenvs` on Windows).
You can change the [`cache-dir`]({{< relref "configuration#cache-dir" >}} "cache-dir configuration documentation") value by editing the poetry config.
Additionally, you can use the [`virtualenvs.in-project`]({{< relref "configuration#virtualenvsin-project" >}} "#virtualenvs.in-project configuration documentation") configuration variable
to create virtual environment within your project directory.


There are several ways to run commands within this virtual environment.


### Using `poetry run`

To run your script simply use `poetry run python your_script.py`.
Likewise if you have command line tools such as `pytest` or `black` you can run them using `poetry run pytest`.

### Activating the virtual environment

The easiest way to activate the virtual environment is to create a new shell with `poetry shell`.
To deactivate the virtual environment and exit this new shell type `exit`.
To deactivate the virtual environment without leaving the shell use `deactivate`.

{{% note %}}
**Why a new shell?**

Child processes inherit their environment from their parents, but do not share
them. As such, any modifications made by a child process, is not persisted after
the child process exits. A Python application (Poetry), being a child process,
cannot modify the environment of the shell that it has been called from such
that an activated virtual environment remains active after the Poetry command
has completed execution.

Therefore, Poetry has to create a sub-shell with the virtual environment activated
in order for the subsequent commands to run from within the virtual environment.
{{% /note %}}


Alternatively, to avoid creating a new shell, you can manually activate the
virtual environment by running `source {path_to_venv}/bin/activate` (`{path_to_venv}\Scripts\activate.bat` on Windows).
To get the path to your virtual environment run `poetry env info --path`.
You can also combine these into a nice one-liner, `source $(poetry env info --path)/bin/activate`
To deactivate this virtual environment simply use `deactivate`.

|                   | POSIX Shell                                     | Windows                               | Exit/Deactivate |
| ----------------- | ----------------------------------------------- | ------------------------------------- | --------------- |
| New Shell         | `poetry shell`                                  | `poetry shell`                        | `exit`          |
| Manual Activation | `source {path_to_venv}/bin/activate`            | `{path_to_venv}\Scripts\activate.bat` | `deactivate`    |
| One-liner         | `source $(poetry env info --path)/bin/activate` |                                       | `deactivate`    |


### Version constraints

In our example, we are requesting the `pendulum` package with the version constraint `^2.1`.
This means any version greater or equal to 2.1.0 and less than 3.0.0 (`>=2.1.0 <3.0.0`).

Please read [Dependency specification]({{< relref "dependency-specification" >}} "Dependency specification documentation") for more in-depth information on versions,
how versions relate to each other, and on the different ways you can specify dependencies.


{{% note %}}
**How does Poetry download the right files?**

When you specify a dependency in `pyproject.toml`, Poetry first takes the name of the package
that you have requested and searches for it in any repository you have registered using the `repositories` key.
If you have not registered any extra repositories, or it does not find a package with that name in the
repositories you have specified, it falls back on PyPI.

When Poetry finds the right package, it then attempts to find the best match
for the version constraint you have specified.
{{% /note %}}


## Installing dependencies

To install the defined dependencies for your project, just run the [`install`]({{< relref "cli#install" >}}) command.

```bash
poetry install
```

When you run this command, one of two things may happen:

### Installing without `poetry.lock`

If you have never run the command before and there is also no `poetry.lock` file present,
Poetry simply resolves all dependencies listed in your `pyproject.toml` file and downloads the latest version of their files.

When Poetry has finished installing, it writes all the packages and their exact versions that it downloaded to the `poetry.lock` file,
locking the project to those specific versions.
You should commit the `poetry.lock` file to your project repo so that all people working on the project are locked to the same versions of dependencies (more below).


### Installing with `poetry.lock`

This brings us to the second scenario. If there is already a `poetry.lock` file as well as a `pyproject.toml` file
when you run `poetry install`, it means either you ran the `install` command before,
or someone else on the project ran the `install` command and committed the `poetry.lock` file to the project (which is good).

Either way, running `install` when a `poetry.lock` file is present resolves and installs all dependencies that you listed in `pyproject.toml`,
but Poetry uses the exact versions listed in `poetry.lock` to ensure that the package versions are consistent for everyone working on your project.
As a result you will have all dependencies requested by your `pyproject.toml` file,
but they may not all be at the very latest available versions
(some dependencies listed in the `poetry.lock` file may have released newer versions since the file was created).
This is by design, it ensures that your project does not break because of unexpected changes in dependencies.

### Commit your `poetry.lock` file to version control

Committing this file to VC is important because it will cause anyone who sets up the project
to use the exact same versions of the dependencies that you are using.
Your CI server, production machines, other developers in your team,
everything and everyone runs on the same dependencies,
which mitigates the potential for bugs affecting only some parts of the deployments.
Even if you develop alone, in six months when reinstalling the project you can feel confident
the dependencies installed are still working even if your dependencies released many new versions since then.
(See note below about using the update command.)

{{% note %}}
For libraries it is not necessary to commit the lock file.
{{% /note %}}

### Installing dependencies only

The current project is installed in [editable](https://pip.pypa.io/en/stable/cli/pip_install/#install-editable) mode by default.

If you want to install the dependencies only, run the `install` command with the `--no-root` flag:

```bash
poetry install --no-root
```

## Updating dependencies to their latest versions

As mentioned above, the `poetry.lock` file prevents you from automatically getting the latest versions
of your dependencies.
To update to the latest versions, use the `update` command.
This will fetch the latest matching versions (according to your `pyproject.toml` file)
and update the lock file with the new versions.
(This is equivalent to deleting the `poetry.lock` file and running `install` again.)

{{% note %}}
Poetry will display a **Warning** when executing an install command if `poetry.lock` and `pyproject.toml`
are not synchronized.
{{% /note %}}
