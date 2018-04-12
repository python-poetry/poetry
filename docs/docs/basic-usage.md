# Basic usage

For the basic usage introduction we will be installing `pendulum`, a datetime library.
If you have not yet installed Poetry, refer to the [Introduction](/) chapter.

## Project setup

First, let's create our new project, let's call it `poetry-demo`:

```bash
poetry new poetry-demo
```

This will create the `poetry-demo` directory with the following content:

```text
poetry-demo
├── pyproject.toml
├── README.rst
├── poetry_demo
│   └── __init__.py
└── tests
    ├── __init__.py
    └── test_poetry_demo
```

The `pyproject.toml` file is what is the most important here. This will orchestrate
your project and its dependencies. For now, it looks like this:

```toml
[tool.poetry]
name = "poetry-demo"
version = "0.1.0"
authors = [ "Sébastien Eustace <sebastien@eustace.io>",]

[tool.poetry.dependencies]

[tool.poetry.dev-dependencies]
pytest = "^3.4"
```

### Specifying dependencies

If you want to add dependencies to your project, you can specify them in the `tool.poetry.dependencies` section.

```toml
[tool.poetry.dependencies]
pendulum = "^1.4"
```

As you can see, it takes a mapping of **package names** and **version constraints**.

Poetry uses this information to search for the right set of files in package "repositories" that you register
in the `tool.poetry.repositories` section, or on [PyPI](https://pypi.org) by default.

Also, instead of modifying the `pyproject.toml` file by hand, you can use the `add` command.
    
```bash
$ poetry add pendulum
```

It will automatically find a suitable version constraint.

!!!warning

    `poetry` uses the PyPI JSON API to retrieve package information.
    
    However, some packages (like `boto3` for example) have missing dependency
    information due to bad packaging/publishing which means that `poetry` won't
    be able to properly resolve dependencies.
    
    To workaround it, `poetry` has a fallback mechanism that will download packages
    distributions to check the dependencies.
    
    While, in most cases, it will lead to a more exhaustive dependency resolution
    it will also considerably slow down the process (up to 30 minutes in some extreme cases
    like `boto3`).
    
    If you do not want the fallback mechanism, you can deactivate it like so.
    
    ```bash
    poetry config settings.pypi.fallback false
    ```
    
    In this case you will need to specify the missing dependencies in you `pyproject.toml`
    file.
    
    Any case of missing dependencies should be reported to https://github.com/sdispater/poetry/issues
    and on the repository of the main package.

### Version constraints

In our example, we are requesting the `pendulum` package with the version constraint `^1.4`.
This means any version geater or equal to 1.4.0 and less than 2.0.0 (`>=1.4.0 <2.0.0`).

Please read [versions](/versions/) for more in-depth information on versions, how versions relate to each other, and on version constraints.


!!!note

    **How does Poetry download the right files?**
    
    When you specify a dependency in `pyproject.toml`, Poetry first take the name of the package
    that you have requested and searches for it in any repository you have registered using the `repositories` key.
    If you have not registered any extra repositories, or it does not find a package with that name in the
    repositories you have specified, it falls bask on PyPI.
    
    When Poetry finds the right package, it then attempts to find the best match
    for the version constraint you have specified.
    

## Installing dependencies

To install the defined dependencies for your project, just run the `install` command.
    
```bash
poetry install
```

When you run this command, one of two things may happen:

### Installing without `pyproject.lock`

If you have never run the command before and there is also no `pyproject.lock` file present,
Poetry simply resolves all dependencies listed in your `pyproject.toml` file and downloads the latest version of their files.

When Poetry has finished installing, it writes all of the packages and the exact versions of them that it downloaded to the `pyproject.lock` file,
locking the project to those specific versions.
You should commit the `pyproject.lock` file to your project repo so that all people working on the project are locked to the same versions of dependencies (more below).


### Installing with `pyproject.lock`

This brings us to the second scenario. If there is already a `pyproject.lock` file as well as a `pyproject.toml` file
when you run `poetry install`, it means either you ran the `install` command before,
or someone else on the project ran the `install` command and committed the `pyproject.lock` file to the project (which is good).

Either way, running `install` when a `pyproject.lock` file is present resolves and installs all dependencies that you listed in `pyproject.toml`,
but Poetry uses the exact versions listed in `pyproject.lock` to ensure that the package versions are consistent for everyone working on your project.
As a result you will have all dependencies requested by your `pyproject.toml` file,
but they may not all be at the very latest available versions
(some of the dependencies listed in the `pyproject.lock` file may have released newer versions since the file was created).
This is by design, it ensures that your project does not break because of unexpected changes in dependencies.

### Commit your `pyproject.lock` file to version control

Committing this file to VC is important because it will cause anyone who sets up the project
to use the exact same versions of the dependencies that you are using.
Your CI server, production machines, other developers in your team,
everything and everyone runs on the same dependencies,
which mitigates the potential for bugs affecting only some parts of the deployments.
Even if you develop alone, in six months when reinstalling the project you can feel confident
the dependencies installed are still working even if your dependencies released many new versions since then.
(See note below about using the update command.)

!!!note

    For libraries it is not necessary to commit the lock file.
    

## Updating dependencies to their latest versions

As mentioned above, the `pyproject.lock` file prevents you from automatically getting the latest versions
of your dependencies.
To update to the latest versions, use the `update` command.
This will fetch the latest matching versions (according to your `pyproject.toml` file)
and update the lock file with the new versions.
(This is equivalent to deleting the `pyproject.lock` file and running `install` again.)

!!!note

    Poetry will display a Warning when executing an install command if `pyproject.lock` and `pyproject.toml`
    are not synchronized.


## Poetry and virtualenvs

When you execute the `install` command (or any other "install" commands like `add` or `remove`),
Poetry will check if it's currently inside a virtualenv and, if not, will use an existing one
or create a brand new one for you to always work isolated from your global Python installation.

!!!note

    The created virtualenv will use the Python executable for which
    `poetry` has been installed.
