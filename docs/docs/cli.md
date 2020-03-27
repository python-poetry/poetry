# Commands

You've already learned how to use the command-line interface to do some things.
This chapter documents all the available commands.

To get help from the command-line, simply call `poetry` to see the complete list of commands,
then `--help` combined with any of those can give you more information.

As `Poetry` uses [cleo](https://github.com/sdispater/cleo) you can call commands by short name if it's not ambiguous.

```bash
poetry up
```

calls `poetry update`.


## Global options

* `--verbose (-v|vv|vvv)`: Increase the verbosity of messages: "-v" for normal output, "-vv" for more verbose output and "-vvv" for debug.
* `--help (-h)` : Display help information.
* `--quiet (-q)` : Do not output any message.
* `--ansi`: Force ANSI output.
* `--no-ansi`: Disable ANSI output.
* `--version (-V)`: Display this application version.


## new

This command will help you kickstart your new Python project by creating
a directory structure suitable for most projects.

```bash
poetry new my-package
```

will create a folder as follows:

```text
my-package
├── pyproject.toml
├── README.rst
├── my_package
│   └── __init__.py
└── tests
    ├── __init__.py
    └── test_my_package.py
```

If you want to name your project differently than the folder, you can pass
the `--name` option:

```bash
poetry new my-folder --name my-package
```

If you want to use a src folder, you can use the `--src` option:

```bash
poetry new --src my-package
```

That will create a folder structure as follows:

```text
my-package
├── pyproject.toml
├── README.rst
├── src
│   └── my_package
│       └── __init__.py
└── tests
    ├── __init__.py
    └── test_my_package.py
```

## init

This command will help you create a `pyproject.toml` file interactively
by prompting you to provide basic information about your package.

It will interactively ask you to fill in the fields, while using some smart defaults.

```bash
poetry init
```

### Options

* `--name`: Name of the package.
* `--description`: Description of the package.
* `--author`: Author of the package.
* `--dependency`: Package to require with a version constraint. Should be in format `foo:1.0.0`.
* `--dev-dependency`: Development requirements, see `--require`.


## install

The `install` command reads the `pyproject.toml` file from the current project,
resolves the dependencies, and installs them.

```bash
poetry install
```

If there is a `poetry.lock` file in the current directory,
it will use the exact versions from there instead of resolving them.
This ensures that everyone using the library will get the same versions of the dependencies.

If there is no `poetry.lock` file, Poetry will create one after dependency resolution.

You can specify to the command that you do not want the development dependencies installed by passing
the `--no-dev` option.

```bash
poetry install --no-dev
```

You can also specify the extras you want installed
by passing the `--E|--extras` option (See [Extras](#extras) for more info)

```bash
poetry install --extras "mysql pgsql"
poetry install -E mysql -E pgsql
```

By default `poetry` will install your project's package everytime you run `install`:

```bash
$ poetry install
Installing dependencies from lock file

No dependencies to install or update

  - Installing <your-package-name> (x.x.x)

```

If you want to skip this installation, use the `--no-root` option.

```bash
poetry install --no-root
```

### Options

* `--no-dev`: Do not install dev dependencies.
* `--no-root`: Do not install the root package (your project).
* `--extras (-E)`: Features to install (multiple values allowed).

## update

In order to get the latest versions of the dependencies and to update the `poetry.lock` file,
you should use the `update` command.

```bash
poetry update
```

This will resolve all dependencies of the project and write the exact versions into `poetry.lock`.

If you just want to update a few packages and not all, you can list them as such:

```bash
poetry update requests toml
```

### Options

* `--dry-run` : Outputs the operations but will not execute anything (implicitly enables --verbose).
* `--no-dev` : Do not install dev dependencies.
* `--lock` : Do not perform install (only update the lockfile).

## add

The `add` command adds required packages to your `pyproject.toml` and installs them.

If you do not specify a version constraint,
poetry will choose a suitable one based on the available package versions.

```bash
poetry add requests pendulum
```

You also can specify a constraint when adding a package, like so:

```bash
poetry add pendulum@^2.0.5
poetry add "pendulum>=2.0.5"
```

If you try to add a package that is already present, you will get an error.
However, if you specify a constraint, like above, the dependency will be updated
by using the specified constraint. If you want to get the latest version of an already
present dependency you can use the special `latest` constraint:

```bash
poetry add pendulum@latest
```

You can also add `git` dependencies:

```bash
poetry add git+https://github.com/sdispater/pendulum.git
```

If you need to checkout a specific branch, tag or revision,
you can specify it when using `add`:

```bash
poetry add git+https://github.com/sdispater/pendulum.git#develop
poetry add git+https://github.com/sdispater/pendulum.git#2.0.5
```

or make them point to a local directory or file:

```bash
poetry add ./my-package/
poetry add ../my-package/dist/my-package-0.1.0.tar.gz
poetry add ../my-package/dist/my_package-0.1.0.whl
```

Path dependencies pointing to a local directory will be installed in editable mode (i.e. setuptools "develop mode").
It means that changes in the local directory will be reflected directly in environment.

If you don't want the dependency to be installed in editable mode you can specify it in the `pyproject.toml` file:

```toml
[tool.poetry.dependencies]
my-package = {path = "../my/path", develop = false}
```

If the package(s) you want to install provide extras, you can specify them
when adding the package:

```bash
poetry add requests[security,socks]
poetry add "requests[security,socks]~=2.22.0"
poetry add "git+https://github.com/pallets/flask.git@1.1.1[dotenv,dev]"
```

### Options

* `--dev (-D)`: Add package as development dependency.
* `--path`: The path to a dependency.
* `--optional` : Add as an optional dependency.
* `--dry-run` : Outputs the operations but will not execute anything (implicitly enables --verbose).


## remove

The `remove` command removes a package from the current
list of installed packages.

```bash
poetry remove pendulum
```

### Options

* `--dev (-D)`: Removes a package from the development dependencies.
* `--dry-run` : Outputs the operations but will not execute anything (implicitly enables --verbose).


## show

To list all of the available packages, you can use the `show` command.

```bash
poetry show
```

If you want to see the details of a certain package, you can pass the package name.

```bash
poetry show pendulum

name        : pendulum
version     : 1.4.2
description : Python datetimes made easy

dependencies:
 - python-dateutil >=2.6.1
 - tzlocal >=1.4
 - pytzdata >=2017.2.2
```

### Options

* `--no-dev`: Do not list the dev dependencies.
* `--tree`: List the dependencies as a tree.
* `--latest (-l)`: Show the latest version.
* `--outdated (-o)`: Show the latest version but only for packages that are outdated.


## build

The `build` command builds the source and wheels archives.

```bash
poetry build
```

Note that, at the moment, only pure python wheels are supported.

### Options

* `--format (-f)`: Limit the format to either `wheel` or `sdist`.

## publish

This command publishes the package, previously built with the [`build`](#build) command, to the remote repository.

It will automatically register the package before uploading if this is the first time it is submitted.

```bash
poetry publish
```

It can also build the package if you pass it the `--build` option.

### Options

* `--repository (-r)`: The repository to register the package to (default: `pypi`).
Should match a repository name set by the [`config`](#config) command.
* `--username (-u)`: The username to access the repository.
* `--password (-p)`: The password to access the repository.

## config

The `config` command allows you to edit poetry config settings and repositories.

```bash
poetry config --list
```

### Usage

````bash
poetry config [options] [setting-key] [setting-value1] ... [setting-valueN]
````

`setting-key` is a configuration option name and `setting-value1` is a configuration value.
See [Configuration](/docs/configuration/) for all available settings.

### Options

* `--unset`: Remove the configuration element named by `setting-key`.
* `--list`: Show the list of current config variables.

## run

The `run` command executes the given command inside the project's virtualenv.

```bash
poetry run python -V
```

It can also execute one of the scripts defined in `pyproject.toml`.

So, if you have a script defined like this:

```toml
[tool.poetry.scripts]
my-script = "my_module:main"
```

You can execute it like so:

```bash
poetry run my-script
```

Note that this command has no option.

## shell

The `shell` command spawns a shell,
according to the `$SHELL` environment variable,
within the virtual environment.
If one doesn't exist yet, it will be created.

```bash
poetry shell
```

## check

The `check` command validates the structure of the `pyproject.toml` file
and returns a detailed report if there are any errors.

```bash
poetry check
```

## search

This command searches for packages on a remote index.

```bash
poetry search requests pendulum
```

### Options

* `--only-name (-N)`: Search only in name.

## lock

This command locks (without installing) the dependencies specified in `pyproject.toml`.

```bash
poetry lock
```

## version

This command shows the current version of the project or bumps the version of
the project and writes the new version back to `pyproject.toml` if a valid
bump rule is provided.

The new version should ideally be a valid semver string or a valid bump rule:
`patch`, `minor`, `major`, `prepatch`, `preminor`, `premajor`, `prerelease`.


## export

This command exports the lock file to other formats.

```bash
poetry export -f requirements.txt > requirements.txt
```

!!!note

    Only the `requirements.txt` format is currently supported.

### Options

* `--format (-f)`: The format to export to.  Currently, only
  `requirements.txt` is supported.
* `--output (-o)`: The name of the output file.  If omitted, print to standard
  output.
* `--dev`: Include development dependencies.
* `--extras (-E)`: Extra sets of dependencies to include.
* `--without-hashes`: Exclude hashes from the exported file.
* `--with-credentials`: Include credentials for extra indices.

## env

The `env` command regroups sub commands to interact with the virtualenvs
associated with a specific project.

See [Managing environments](./managing-environments.md) for more information about these commands.
