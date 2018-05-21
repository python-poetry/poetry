# Poetry: Dependency Management for Python

![Poetry build status](https://travis-ci.org/sdispater/poetry.svg)

Poetry helps you declare, manage and install dependencies of Python projects,
ensuring you have the right stack everywhere.

![Poetry Install](https://raw.githubusercontent.com/sdispater/poetry/master/assets/install.gif)

It supports Python 2.7 and 3.4+.

## Installation

Poetry provides a custom installer that will install `poetry` isolated
from the rest of your system by vendorizing its dependencies. This is the
recommended way of installing `poetry`.

```bash
curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python
```

Alternatively, you can download the `get-poetry.py` file and execute it separately.

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

Updating poetry to the latest stable version is as simple as calling the `self:update` command.

```bash
poetry self:update
```

If you want to install prerelease versions, you can use the `--preview` option.

```bash
poetry self:update --preview
```

And finally, if you want to install a specific version you can pass it as an argument
to `self:update`.

```bash
poetry self:update 0.8.0
```


### Enable tab completion for Bash, Fish, or Zsh

`poetry` supports generating completion scripts for Bash, Fish, and Zsh.
See `poetry help completions` for full details, but the gist is as simple as using one of the following:

```bash
# Bash
poetry completions bash > /etc/bash_completion.d/pyproject.bash-completion

# Bash (macOS/Homebrew)
poetry completions bash > $(brew --prefix)/etc/bash_completion.d/pyproject.bash-completion

# Fish
poetry completions fish > ~/.config/fish/completions/pyproject.fish

# Zsh
poetry completions zsh > ~/.zfunc/_poetry
```

*Note:* you may need to restart your shell in order for the changes to take
effect.

For `zsh`, you must then add the following line in your `~/.zshrc` before
`compinit`:

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

repository = "https://github.com/sdispater/poetry"
homepage = "https://github.com/sdispater/poetry"

keywords = ['packaging', 'poetry']

[tool.poetry.dependencies]
python = "~2.7 || ^3.2"  # Compatible python versions must be declared here
toml = "^0.9"
# Dependencies with extras
requests = { version = "^2.13", extras = [ "security" ] }
# Python specific dependencies with prereleases allowed
pathlib2 = { version = "^2.2", python = "~2.7", allows-prereleases = true }
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

`poetry` also comes with a full fledged dependency resolution library, inspired by [Molinillo](https://github.com/CocoaPods/Molinillo).

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

The dependency resolution is erratic and will fail even is there is a solution. Let's take an example:

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

#### Install command

When you specify a package to the `install` command it will add it as a wildcard
dependency. This means that **any** version of this package can be installed which
can lead to compatibility issues.

Also, you have to explicitly tell it to not update the locked packages when you
installed new ones. This should be the default.

#### Remove command

The `remove` command will only remove the package specified but not its dependencies
if they are no longer needed.

You either have to use `sync` or `clean` to fix that.

#### Too limited in scope

Finally, the `Pipfile` is just a replacement from `requirements.txt` and, in the end, you will still need to
populate your `setup.py` file (or `setup.cfg`) with the exact same dependencies you declared in your `Pipfile`.
So, in the end, you will still need to manage a few configuration files to properly setup your project.


## Commands


### new

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
    └── test_my_package
```

If you want to name your project differently than the folder, you can pass
the `--name` option:

```bash
poetry new my-folder --name my-package
```

### init

This command will help you create a `pyproject.toml` file interactively
by prompting you to provide basic information about your package.

It will interactively ask you to fill in the fields, while using some smart defaults.

```bash
poetry init
```

#### Options

* `--name`: Name of the package.
* `--description`: Description of the package.
* `--author`: Author of the package.
* `--dependency`: Package to require with a version constraint. Should be in format `foo:1.0.0`.
* `--dev-dependency`: Development requirements, see `--require`.

### install

The `install` command reads the `pyproject.toml` file from the current directory, resolves the dependencies,
and installs them.

```bash
poetry install
```

If there is a `pyproject.lock` file in the current directory,
it will use the exact versions from there instead of resolving them.
This ensures that everyone using the library will get the same versions of the dependencies.

If there is no `pyproject.lock` file, Poetry will create one after dependency resolution.

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

#### Options

* `--no-dev`: Do not install dev dependencies.
* `-E|--extras`: Features to install (multiple values allowed).

### update

In order to get the latest versions of the dependencies and to update the `pyproject.lock` file,
you should use the `update` command.

```bash
poetry update
```

This will resolve all dependencies of the project and write the exact versions into `pyproject.lock`.

If you just want to update a few packages and not all, you can list them as such:

```bash
poetry update requests toml
```

#### Options

* `--dry-run` : Outputs the operations but will not execute anything (implicitly enables --verbose).

### add

The `add` command adds required packages to your `pyproject.toml` and installs them.

If you do not specify a version constraint,
poetry will choose a suitable one based on the available package versions.

```bash
poetry add requests pendulum
```

#### Options

* `--D|dev`: Add package as development dependency.
* `--optional` : Add as an optional dependency.
* `--dry-run` : Outputs the operations but will not execute anything (implicitly enables --verbose).


### remove

The `remove` command removes a package from the current
list of installed packages

```bash
poetry remove pendulum
```

#### Options

* `--D|dev`: Removes a package from the development dependencies.
* `--dry-run` : Outputs the operations but will not execute anything (implicitly enables --verbose).


### show

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

#### Options

* `--tree`: List the dependencies as a tree.
* `-l|--latest`: Show the latest version.
*  `-o|--outdated`: Show the latest version but only for packages that are outdated.


### build

The `build` command builds the source and wheels archives.

```bash
poetry build
```

Note that, at the moment, only pure python wheels are supported.

#### Options

* `-F|--format`: Limit the format to either wheel or sdist.

### publish

This command builds (if not already built) and publishes the package to the remote repository.

It will automatically register the package before uploading if this is the first time it is submitted.

```bash
poetry publish
```

#### Options

* `-r|--repository`: The repository to register the package to (default: `pypi`).
Should match a repository name set by the [`config`](#config) command.
* `--username (-u)`: The username to access the repository.
* `--password (-p)`: The password to access the repository.


### `config`

The `config` command allows you to edit poetry config settings and repositories.

```bash
poetry config --list
```

#### Usage

````bash
poetry config [options] [setting-key] [setting-value1] ... [setting-valueN]
````

`setting-key` is a configuration option name and `setting-value1` is a configuration value.

#### Modifying repositories

In addition to modifying the config section,
the config command also supports making changes to the repositories section by using it the following way:

```bash
poetry config repositories.foo https://foo.bar/simple/
```

This will set the url for repository `foo` to `https://foo.bar/simple/`.

If you want to store your credentials for a specific repository, you can do so easily:

```bash
poetry config http-basic.foo username password
```

If you do not specify the password you will be prompted to write it.

#### Options

* `--unset`: Remove the configuration element named by `setting-key`.
* `--list`: Show the list of current config variables.

### search

This command searches for packages on a remote index.

```bash
poetry search requests pendulum
```

#### Options

* `-N|--only-name`: Search only in name.

### lock

This command locks (without installing) the dependencies specified in `pyproject.toml`.

```bash
poetry lock
```


## The `pyproject.toml` file

The `tool.poetry` section of the `pyproject.toml` file is composed of multiple sections.

#### name

The name of the package. **Required**

#### version

The version of the package. **Required**

This should follow [semantic versioning](http://semver.org/). However it will not be enforced and you remain
free to follow another specification.

#### description

A short description of the package. **Required**

#### license

The license of the package.

The recommended notation for the most common licenses is (alphabetical):

* Apache-2.0
* BSD-2-Clause
* BSD-3-Clause
* BSD-4-Clause
* GPL-2.0
* GPL-2.0+
* GPL-3.0
* GPL-3.0+
* LGPL-2.1
* LGPL-2.1+
* LGPL-3.0
* LGPL-3.0+
* MIT

Optional, but it is highly recommended to supply this.
More identifiers are listed at the [SPDX Open Source License Registry](https://www.spdx.org/licenses/).

#### authors

The authors of the package. This is a list of authors and should contain at least one author.

Authors must be in the form `name <email>`.

#### readme

The readme file of the package. **Required**

The file can be either `README.rst` or `README.md`.

#### homepage

An URL to the website of the project. **Optional**

#### repository

An URL to the repository of the project. **Optional**

#### documentation

An URL to the documentation of the project. **Optional**

#### keywords

A list of keywords (max: 5) that the package is related to. **Optional**

#### include and exclude

A list of patterns that will be included in the final package.

You can explicitly specify to Poetry that a set of globs should be ignored or included for the purposes of packaging.
The globs specified in the exclude field identify a set of files that are not included when a package is built.

If a VCS is being used for a package, the exclude field will be seeded with the VCS’ ignore settings (`.gitignore` for git for example).

```toml
[tool.poetry]
# ...
include = ["package/**/*.py", "package/**/.c"]
```

```toml
exclude = ["package/excluded.py"]
```

### `dependencies` and `dev-dependencies`

Poetry is configured to look for dependencies on [PyPi](https://pypi.org) by default.
Only the name and a version string are required in this case.

```toml
[tool.poetry.dependencies]
requests = "^2.13.0"
```

If you want to use a private repository, you can add it to your `pyproject.toml` file, like so:

```toml
[[tool.poetry.source]]
name = 'private'
url = 'http://example.com/simple'
```

Be aware that declaring the python version for which your package
is compatible is mandatory:

```toml
[tool.poetry.dependencies]
python = "^3.6"
```

#### Caret requirement

**Caret requirements** allow SemVer compatible updates to a specified version.
An update is allowed if the new version number does not modify the left-most non-zero digit in the major, minor, patch grouping.
In this case, if we ran `poetry update requests`, poetry would update us to version `2.14.0` if it was available,
but would not update us to `3.0.0`.
If instead we had specified the version string as `^0.1.13`, poetry would update to `0.1.14` but not `0.2.0`.
`0.0.x` is not considered compatible with any other version.

Here are some more examples of caret requirements and the versions that would be allowed with them:

```text
^1.2.3 := >=1.2.3 <2.0.0
^1.2 := >=1.2.0 <2.0.0
^1 := >=1.0.0 <2.0.0
^0.2.3 := >=0.2.3 <0.3.0
^0.0.3 := >=0.0.3 <0.0.4
^0.0 := >=0.0.0 <0.1.0
^0 := >=0.0.0 <1.0.0
```

#### Tilde requirements

**Tilde requirements** specify a minimal version with some ability to update.
If you specify a major, minor, and patch version or only a major and minor version, only patch-level changes are allowed.
If you only specify a major version, then minor- and patch-level changes are allowed.

`~1.2.3` is an example of a tilde requirement.

```text
~1.2.3 := >=1.2.3 <1.3.0
~1.2 := >=1.2.0 <1.3.0
~1 := >=1.0.0 <2.0.0
```

#### Wildcard requirements

**Wildcard requirements** allow for any version where the wildcard is positioned.

`*`, `1.*` and `1.2.*` are examples of wildcard requirements.

```text
* := >=0.0.0
1.* := >=1.0.0 <2.0.0
1.2.* := >=1.2.0 <1.3.0
```

#### Inequality requirements

**Inequality requirements** allow manually specifying a version range or an exact version to depend on.

Here are some examples of inequality requirements:

```text
>= 1.2.0
> 1
< 2
!= 1.2.3
```

#### Multiple requirements

Multiple version requirements can also be separated with a comma, e.g. `>= 1.2, < 1.5`.

#### `git` dependencies

To depend on a library located in a `git` repository,
the minimum information you need to specify is the location of the repository with the git key:

```toml
[tool.poetry.dependencies]
requests = { git = "https://github.com/requests/requests.git" }
```

Since we haven’t specified any other information,
Poetry assumes that we intend to use the latest commit on the `master` branch to build our project.
You can combine the `git` key with the `rev`, `tag`, or `branch` keys to specify something else.
Here's an example of specifying that you want to use the latest commit on a branch named `next`:

```toml
[tool.poetry.dependencies]
requests = { git = "https://github.com/kennethreitz/requests.git", branch = "next" }
```

#### Python restricted dependencies

You can also specify that a dependency should be installed only for specific Python versions:

```toml
[tool.poetry.dependencies]
pathlib2 = { version = "^2.2", python = "~2.7" }
```

```toml
[tool.poetry.dependencies]
pathlib2 = { version = "^2.2", python = ["~2.7", "^3.2"] }
```

### `scripts`

This section describe the scripts or executable that will be installed when installing the package

```toml
[tool.poetry.scripts]
poetry = 'poetry:console.run'
```

After installing a package with the above toml, `poetry` will be a global command available from the command line that will execute `console.run` in the `poetry` package.

### `extras`

Poetry supports extras to allow expression of:

* optional dependencies, which enhance a package, but are not required; and
* clusters of optional dependencies.

```toml
[tool.poetry]
name = "awesome"

[tool.poetry.dependencies]
# These packages are mandatory and form the core of this package’s distribution.
mandatory = "^1.0"

# A list of all of the optional dependencies, some of which are included in the
# below `extras`. They can be opted into by apps.
psycopg2 = { version = "^2.7", optional = true }
mysqlclient = { version = "^1.3", optional = true }

[tool.poetry.extras]
mysql = ["mysqlclient"]
pgsql = ["psycopg2"]
```

When installing packages, you can specify extras by using the `-E|--extras` option:

```bash
poetry install --extras "mysql pgsql"
poetry install -E mysql -E pgsql
```

### `plugins`

Poetry supports arbitrary plugins which work similarly to
[setuptools entry points](http://setuptools.readthedocs.io/en/latest/setuptools.html).
To match the example in the setuptools documentation, you would use the following:

```toml
[tool.poetry.plugins] # Optional super table

[tool.poetry.plugins."blogtool.parsers"]
".rst" = "some_module::SomeClass"
```

## Resources

* [Official Website](https://poetry.eustace.io)
* [Issue Tracker](https://github.com/sdispater/poetry/issues)
