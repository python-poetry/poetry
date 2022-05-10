---
title: "Commands"
draft: false
type: docs
layout: single

menu:
  docs:
    weight: 30
---


# Commands

You've already learned how to use the command-line interface to do some things.
This chapter documents all the available commands.

To get help from the command-line, simply call `poetry` to see the complete list of commands,
then `--help` combined with any of those can give you more information.

## Global options

* `--verbose (-v|vv|vvv)`: Increase the verbosity of messages: "-v" for normal output, "-vv" for more verbose output and "-vvv" for debug.
* `--help (-h)` : Display help information.
* `--quiet (-q)` : Do not output any message.
* `--ansi`: Force ANSI output.
* `--no-ansi`: Disable ANSI output.
* `--version (-V)`: Display this application version.
* `--no-interaction (-n)`: Do not ask any interactive question.
* `--no-plugins`: Disables plugins.
* `--no-cache`: Disables Poetry source caches.


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
├── README.md
├── my_package
│   └── __init__.py
└── tests
    └── __init__.py
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
├── README.md
├── src
│   └── my_package
│       └── __init__.py
└── tests
    └── __init__.py
```

The `--name` option is smart enough to detect namespace packages and create
the required structure for you.

```bash
poetry new --src --name my.package my-package
```

will create the following structure:

```text
my-package
├── pyproject.toml
├── README.md
├── src
│   └── my
│       └── package
│           └── __init__.py
└── tests
    └── __init__.py
```

### Options

* `--name`: Set the resulting package name.
* `--src`: Use the src layout for the project.
* `--readme`: Specify the readme file format. One of `md` (default) or `rst`.


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
* `--python` Compatible Python versions.
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

If you want to exclude one or more dependency group for the installation, you can use
the `--without` option.

```bash
poetry install --without test,docs
```

{{% note %}}
The `--no-dev` option is now deprecated. You should use the `--without dev` notation instead.
{{% /note %}}

You can also select optional dependency groups with the `--with` option.

```bash
poetry install --with test,docs
```

It's also possible to only install specific dependency groups by using the `only` option.

```bash
poetry install --only test,docs
```

{{% note %}}
The `--dev-only` option is now deprecated. You should use the `--only dev` notation instead.
{{% /note %}}

See [Dependency groups]({{< relref "managing-dependencies#dependency-groups" >}}) for more information
about dependency groups.

If you want to synchronize your environment – and ensure it matches the lock file – use the
`--sync` option.

```bash
poetry install --sync
```

The `--sync` can be combined with group-related options:

```bash
poetry install --without dev --sync
poetry install --with docs --sync
poetry install --only dev
```

You can also specify the extras you want installed
by passing the `-E|--extras` option (See [Extras]({{< relref "pyproject#extras" >}}) for more info)

```bash
poetry install --extras "mysql pgsql"
poetry install -E mysql -E pgsql
```

By default `poetry` will install your project's package every time you run `install`:

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

Installation of your project's package is also skipped when the `--only`
option is used.

### Options

* `--without`: The dependency groups to ignore.
* `--with`: The optional dependency groups to include.
* `--only`: The only dependency groups to include.
* `--default`: Only include the main dependencies. (**Deprecated**)
* `--sync`: Synchronize the environment with the locked packages and the specified groups.
* `--no-root`: Do not install the root package (your project).
* `--dry-run`: Output the operations but do not execute anything (implicitly enables --verbose).
* `--extras (-E)`: Features to install (multiple values allowed).
* `--no-dev`: Do not install dev dependencies. (**Deprecated**)
* `--dev-only`: Only install dev dependencies. (**Deprecated**)
* `--remove-untracked`: Remove dependencies not presented in the lock file. (**Deprecated**)

{{% note %}}
When `--only` is specified, `--with` and `--without` options are ignored.
{{% /note %}}

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

Note that this will not update versions for dependencies outside their version constraints specified
in the `pyproject.toml` file. In other terms, `poetry update foo` will be a no-op if the version constraint
specified for `foo` is `~2.3` or `2.3` and `2.4` is available. In order for `foo` to be updated, you must
update the constraint, for example `^2.3`. You can do this using the `add` command.

### Options

* `--without`: The dependency groups to ignore.
* `--with`: The optional dependency groups to include.
* `--only`: The only dependency groups to include.
* `--default`: Only include the main dependencies. (**Deprecated**)
* `--dry-run` : Outputs the operations but will not execute anything (implicitly enables --verbose).
* `--no-dev` : Do not update the development dependencies. (**Deprecated**)
* `--lock` : Do not perform install (only update the lockfile).

{{% note %}}
When `--only` is specified, `--with` and `--without` options are ignored.
{{% /note %}}

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

or use ssh instead of https:

```bash
poetry add git+ssh://git@github.com/sdispater/pendulum.git

or alternatively:

poetry add git+ssh://git@github.com:sdispater/pendulum.git
```

If you need to checkout a specific branch, tag or revision,
you can specify it when using `add`:

```bash
poetry add git+https://github.com/sdispater/pendulum.git#develop
poetry add git+https://github.com/sdispater/pendulum.git#2.0.5

or using SSH instead:

poetry add git+ssh://github.com/sdispater/pendulum.git#develop
poetry add git+ssh://github.com/sdispater/pendulum.git#2.0.5
```

or make them point to a local directory or file:

```bash
poetry add ./my-package/
poetry add ../my-package/dist/my-package-0.1.0.tar.gz
poetry add ../my-package/dist/my_package-0.1.0.whl
```

If you want the dependency to be installed in editable mode you can use the `--editable` option.

```bash
poetry add --editable ./my-package/
poetry add --editable git+ssh://github.com/sdispater/pendulum.git#develop
```

Alternatively, you can specify it in the `pyproject.toml` file. It means that changes in the local directory will be reflected directly in environment.

```toml
[tool.poetry.dependencies]
my-package = {path = "../my/path", develop = true}
```

{{% note %}}
Before poetry 1.1 path dependencies were installed in editable mode by default. You should always set the `develop` attribute explicit,
to make sure the behavior is the same for all poetry versions.
{{% /note %}}

If the package(s) you want to install provide extras, you can specify them
when adding the package:

```bash
poetry add requests[security,socks]
poetry add "requests[security,socks]~=2.22.0"
poetry add "git+https://github.com/pallets/flask.git@1.1.1[dotenv,dev]"
```

If you want to add a package to a specific group of dependencies, you can use the `--group (-G)` option:

```bash
poetry add mkdocs --group docs
```

See [Dependency groups]({{< relref "managing-dependencies#dependency-groups" >}}) for more information
about dependency groups.

### Options

* `--group (-G)`: The group to add the dependency to.
* `--dev (-D)`: Add package as development dependency. (**Deprecated**)
* `--editable (-e)`: Add vcs/path dependencies as editable.
* `--extras (-E)`: Extras to activate for the dependency. (multiple values allowed)
* `--optional`: Add as an optional dependency.
* `--python`: Python version for which the dependency must be installed.
* `--platform`: Platforms for which the dependency must be installed.
* `--source`: Name of the source to use to install the package.
* `--allow-prereleases`: Accept prereleases.
* `--dry-run`: Output the operations but do not execute anything (implicitly enables --verbose).
* `--lock`: Do not perform install (only update the lockfile).


## remove

The `remove` command removes a package from the current
list of installed packages.

```bash
poetry remove pendulum
```

If you want to remove a package from a specific group of dependencies, you can use the `--group (-G)` option:

```bash
poetry remove mkdocs --group docs
```

See [Dependency groups]({{< relref "managing-dependencies#dependency-groups" >}}) for more information
about dependency groups.

### Options

* `--group (-G)`: The group to remove the dependency from.
* `--dev (-D)`: Removes a package from the development dependencies. (**Deprecated**)
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

dependencies
 - python-dateutil >=2.6.1
 - tzlocal >=1.4
 - pytzdata >=2017.2.2

required by
 - calendar >=1.4.0
```

### Options

* `--without`: The dependency groups to ignore.
* `--why`: Include reverse dependencies where applicable.
* `--with`: The optional dependency groups to include.
* `--only`: The only dependency groups to include.
* `--default`: Only include the main dependencies. (**Deprecated**)
* `--no-dev`: Do not list the dev dependencies. (**Deprecated**)
* `--tree`: List the dependencies as a tree.
* `--latest (-l)`: Show the latest version.
* `--outdated (-o)`: Show the latest version but only for packages that are outdated.

{{% note %}}
When `--only` is specified, `--with` and `--without` options are ignored.
{{% /note %}}

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
* `--dry-run`: Perform all actions except upload the package.
* `--skip-existing`: Ignore errors from files already existing in the repository.

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
See [Configuration]({{< relref "configuration" >}}) for all available settings.

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

Note that this commmand starts a new shell and activates the virtual environment.

As such, `exit` should be used to properly exit the shell and the virtual environment instead of `deactivate`.

## check

The `check` command validates the structure of the `pyproject.toml` file
and returns a detailed report if there are any errors.

{{% note %}}
This command is also available as a pre-commit hook. See [pre-commit hooks](/docs/pre-commit-hooks#poetry-check) for more information.
{{% /note %}}

```bash
poetry check
```

## search

This command searches for packages on a remote index.

```bash
poetry search requests pendulum
```

## lock

This command locks (without installing) the dependencies specified in `pyproject.toml`.

{{% note %}}
By default, this will lock all dependencies to the latest available compatible versions. To only refresh the lock file, use the `--no-update` option.
This command is also available as a pre-commit hook. See [pre-commit hooks](/docs/pre-commit-hooks#poetry-lock) for more information.
{{% /note %}}

```bash
poetry lock
```

### Options

* `--check`: Verify that `poetry.lock` is consistent with `pyproject.toml`
* `--no-update`: Do not update locked versions, only refresh lock file.

## version

This command shows the current version of the project or bumps the version of
the project and writes the new version back to `pyproject.toml` if a valid
bump rule is provided.

The new version should be a valid [PEP 440](https://peps.python.org/pep-0440/)
string or a valid bump rule: `patch`, `minor`, `major`, `prepatch`, `preminor`,
`premajor`, `prerelease`.

{{% note %}}

If you would like to use semantic versioning for your project, please see
[here]({{< relref "libraries#versioning" >}}).

{{% /note %}}

The table below illustrates the effect of these rules with concrete examples.

| rule       | before  | after   |
| ---------- |---------|---------|
| major      | 1.3.0   | 2.0.0   |
| minor      | 2.1.4   | 2.2.0   |
| patch      | 4.1.1   | 4.1.2   |
| premajor   | 1.0.2   | 2.0.0a0 |
| preminor   | 1.0.2   | 1.1.0a0 |
| prepatch   | 1.0.2   | 1.0.3a0 |
| prerelease | 1.0.2   | 1.0.3a0 |
| prerelease | 1.0.3a0 | 1.0.3a1 |
| prerelease | 1.0.3b0 | 1.0.3b1 |

### Options

* `--short (-s)`: Output the version number only.

## export

This command exports the lock file to other formats.

```bash
poetry export -f requirements.txt --output requirements.txt
```

{{% note %}}
This command is provided by the [Export Poetry Plugin](https://github.com/python-poetry/poetry-plugin-export)
and is also available as a pre-commit hook. See [pre-commit hooks](/docs/pre-commit-hooks#poetry-export) for more information.
{{% /note %}}

{{% note %}}
Unlike the `install` command, this command only includes the project's dependencies defined in the implicit `main`
group defined in `tool.poetry.dependencies` when used without specifying any options.
{{% /note %}}

### Options

* `--format (-f)`: The format to export to (default: `requirements.txt`).
  Currently, only `requirements.txt` is supported.
* `--output (-o)`: The name of the output file.  If omitted, print to standard
  output.
* `--dev`: Include development dependencies. (**Deprecated**)
* `--extras (-E)`: Extra sets of dependencies to include.
* `--without`: The dependency groups to ignore.
* `--with`: The optional dependency groups to include.
* `--only`: The only dependency groups to include.
* `--default`: Only include the main dependencies. (**Deprecated**)
* `--without-hashes`: Exclude hashes from the exported file.
* `--without-urls`: Exclude source repository urls from the exported file.
* `--with-credentials`: Include credentials for extra indices.

## env

The `env` command regroups sub commands to interact with the virtualenvs
associated with a specific project.

See [Managing environments]({{< relref "managing-environments" >}}) for more information about these commands.

## cache

The `cache` command regroups sub commands to interact with Poetry's cache.

### cache list

The `cache list` command lists Poetry's available caches.

```bash
poetry cache list
```

### cache clear

The `cache clear` command removes packages from a cached repository.

For example, to clear the whole cache of packages from the `pypi` repository, run:

```bash
poetry cache clear pypi --all
```

To only remove a specific package from a cache, you have to specify the cache entry in the following form `cache:package:version`:

```bash
poetry cache clear pypi:requests:2.24.0
```

## plugin

The `plugin` namespace regroups sub commands to manage Poetry plugins.

### `plugin add`

The `plugin add` command installs Poetry plugins and make them available at runtime.

For example, to install the `poetry-plugin` plugin, you can run:

```bash
poetry plugin add poetry-plugin
```

The package specification formats supported by the `plugin add` command are the same as the ones supported
by the [`add` command](#add).

If you just want to check what would happen by installing a plugin, you can use the `--dry-run` option

```bash
poetry plugin add poetry-plugin --dry-run
```

#### Options

* `--dry-run`: Outputs the operations but will not execute anything (implicitly enables --verbose).

### `plugin show`

The `plugin show` command lists all the currently installed plugins.

```bash
poetry plugin show
```

### `plugin remove`

The `plugin remove` command removes installed plugins.

```bash
poetry plugin remove poetry-plugin
```

## source

The `source` namespace regroups sub commands to manage repository sources for a Poetry project.

### `source add`

The `source add` command adds source configuration to the project.

For example, to add the `pypi-test` source, you can run:

```bash
poetry source add pypi-test https://test.pypi.org/simple/
```

{{% note %}}
You cannot use the name `pypi` as it is reserved for use by the default PyPI source.
{{% /note %}}

#### Options

* `--default`: Set this source as the [default]({{< relref "repositories#disabling-the-pypi-repository" >}}) (disable PyPI).
* `--secondary`: Set this source as a [secondary]({{< relref "repositories#install-dependencies-from-a-private-repository" >}}) source.

{{% note %}}
You cannot set a source as both `default` and `secondary`.
{{% /note %}}

### `source show`

The `source show` command displays information on all configured sources for the project.

```bash
poetry source show
```

Optionally, you can show information of one or more sources by specifying their names.

```bash
poetry source show pypi-test
```

{{% note %}}
This command will only show sources configured via the `pyproject.toml` and does not include PyPI.
{{% /note %}}

### `source remove`

The `source remove` command removes a configured source from your `pyproject.toml`.

```bash
poetry source remove pypi-test
```
