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

## Global Options

* `--verbose (-v|vv|vvv)`: Increase the verbosity of messages: "-v" for normal output, "-vv" for more verbose output and "-vvv" for debug.
* `--help (-h)` : Display help information.
* `--quiet (-q)` : Do not output any message.
* `--ansi`: Force ANSI output.
* `--no-ansi`: Disable ANSI output.
* `--version (-V)`: Display this application version.
* `--no-interaction (-n)`: Do not ask any interactive question.
* `--no-plugins`: Disables plugins.
* `--no-cache`: Disables Poetry source caches.
* `--directory=DIRECTORY (-C)`: The working directory for the Poetry command (defaults to the current working directory). All command-line arguments will be resolved relative to the given directory.
* `--project=PROJECT (-P)`: Specify another path as the project root. All command-line arguments will be resolved relative to the current working directory or directory specified using `--directory` option if used.

## about

The `about` command displays global information about Poetry, including the current version and version of `poetry-core`.

```bash
poetry about
```

## add

The `add` command adds required packages to your `pyproject.toml` and installs them.

If you do not specify a version constraint,
poetry will choose a suitable one based on the available package versions.

```bash
poetry add requests pendulum
```

{{% note %}}
A package is looked up, by default, only from [PyPI](https://pypi.org).
You can modify the default source (PyPI);
or add and use [Supplemental Package Sources]({{< relref "repositories/#supplemental-package-sources" >}})
or [Explicit Package Sources]({{< relref "repositories/#explicit-package-sources" >}}).

For more information, refer to the [Package Sources]({{< relref "repositories/#package-sources" >}}) documentation.
{{% /note %}}

You can also specify a constraint when adding a package:

```bash
# Allow >=2.0.5, <3.0.0 versions
poetry add pendulum@^2.0.5

# Allow >=2.0.5, <2.1.0 versions
poetry add pendulum@~2.0.5

# Allow >=2.0.5 versions, without upper bound
poetry add "pendulum>=2.0.5"

# Allow only 2.0.5 version
poetry add pendulum==2.0.5
```

{{% note %}}
See the [Dependency specification]({{< relref "dependency-specification#using-the--operator" >}}) page for more information about the `@` operator.
{{% /note %}}

If you try to add a package that is already present, you will get an error.
However, if you specify a constraint, like above, the dependency will be updated
by using the specified constraint.

If you want to get the latest version of an already
present dependency, you can use the special `latest` constraint:

```bash
poetry add pendulum@latest
```

{{% note %}}
See the [Dependency specification]({{< relref "dependency-specification" >}}) for more information on setting the version constraints for a package.
{{% /note %}}

You can also add `git` dependencies:

```bash
poetry add git+https://github.com/sdispater/pendulum.git
```

or use ssh instead of https:

```bash
poetry add git+ssh://git@github.com/sdispater/pendulum.git

# or alternatively:
poetry add git+ssh://git@github.com:sdispater/pendulum.git
```

If you need to checkout a specific branch, tag or revision,
you can specify it when using `add`:

```bash
poetry add git+https://github.com/sdispater/pendulum.git#develop
poetry add git+https://github.com/sdispater/pendulum.git#2.0.5

# or using SSH instead:
poetry add git+ssh://git@github.com:sdispater/pendulum.git#develop
poetry add git+ssh://git@github.com:sdispater/pendulum.git#2.0.5
```

or reference a subdirectory:

```bash
poetry add git+https://github.com/myorg/mypackage_with_subdirs.git@main#subdirectory=subdir
```

You can also add a local directory or file:

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
The `develop` attribute is a Poetry-specific feature, so it is not included in the package distribution metadata.
In other words, it is only considered when using Poetry to install the project.
{{% /note %}}

If the package(s) you want to install provide extras, you can specify them
when adding the package:

```bash
poetry add "requests[security,socks]"
poetry add "requests[security,socks]~=2.22.0"
poetry add "git+https://github.com/pallets/flask.git@1.1.1[dotenv,dev]"
```

{{% warning %}}
Some shells may treat square braces (`[` and `]`) as special characters. It is suggested to always quote arguments containing these characters to prevent unexpected shell expansion.
{{% /warning %}}

If you want to add a package to a specific group of dependencies, you can use the `--group (-G)` option:

```bash
poetry add mkdocs --group docs
```

See [Dependency groups]({{< relref "managing-dependencies#dependency-groups" >}}) for more information
about dependency groups.

#### Options

* `--group (-G)`: The group to add the dependency to.
* `--dev (-D)`: Add package as development dependency. (shortcut for `-G dev`)
* `--editable (-e)`: Add vcs/path dependencies as editable.
* `--extras (-E)`: Extras to activate for the dependency. (multiple values allowed)
* `--optional`: Add as an optional dependency to an extra.
* `--python`: Python version for which the dependency must be installed.
* `--platform`: Platforms for which the dependency must be installed.
* `--markers`: Environment markers which describe when the dependency should be installed.
* `--source`: Name of the source to use to install the package.
* `--allow-prereleases`: Accept prereleases.
* `--dry-run`: Output the operations but do not execute anything (implicitly enables `--verbose`).
* `--lock`: Do not perform install (only update the lockfile).

## build

The `build` command builds the source and wheels archives.

```bash
poetry build
```

The command will trigger the build system defined in the `pyproject.toml` file according to [PEP 517](https://peps.python.org/pep-0517/).
If necessary the build process happens in an isolated environment.

#### Options

* `--format (-f)`: Limit the format to either `wheel` or `sdist`.
* `--clean`: Clean output directory before building.
* `--local-version (-l)`: Add or replace a local version label to the build (deprecated).
* `--output (-o)`: Set output directory for build artifacts. Default is `dist`.
* `--config-settings=<key>=<value> (-c)`: Config settings to be passed to the build back-end. (multiple allowed)

{{% note %}}
When using `--local-version`, the identifier must be [PEP 440](https://peps.python.org/pep-0440/#local-version-identifiers)
compliant. This is useful for adding build numbers, platform specificities etc. for private packages.

`--local-version` is deprecated and will be removed in a future version of Poetry.
Use `--config-settings local-version=<version>` instead.
{{% /note %}}

{{% warning %}}
Local version identifiers SHOULD NOT be used when publishing upstream projects to a public index server, but MAY be
used to identify private builds created directly from the project source.

See [PEP 440](https://peps.python.org/pep-0440/#local-version-identifiers) for more information.
{{% /warning %}}

## cache

The `cache` command groups subcommands to interact with Poetry's cache.

### cache clear

The `cache clear` command removes packages from a cached repository.

For example, to clear the whole cache of packages from the `PyPI` repository, run:

```bash
poetry cache clear PyPI --all
```

To only remove a specific package from a cache, you have to specify the cache entry in the following form `cache:package:version`:

```bash
poetry cache clear pypi:requests:2.24.0
```

### cache list

The `cache list` command lists Poetry's available caches.

```bash
poetry cache list
```

## check

The `check` command validates the content of the `pyproject.toml` file
and its consistency with the `poetry.lock` file.
It returns a detailed report if there are any errors.

{{% note %}}
This command is also available as a pre-commit hook. See [pre-commit hooks]({{< relref "pre-commit-hooks#poetry-check">}}) for more information.
{{% /note %}}

```bash
poetry check
```

#### Options

* `--lock`: Verifies that `poetry.lock` exists for the current `pyproject.toml`.
* `--strict`: Fail if check reports warnings.

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

{{% warning %}}
Use `--` to terminate option parsing if your values may start with a hyphen (`-`), e.g.
```bash
poetry config http-basic.custom-repo gitlab-ci-token -- ${GITLAB_JOB_TOKEN}
```
Without `--` this command will fail if `${GITLAB_JOB_TOKEN}` starts with a hyphen.
{{% /warning%}}

#### Options

* `--unset`: Remove the configuration element named by `setting-key`.
* `--list`: Show the list of current config variables.
* `--local`: Set/Get settings that are specific to a project (in the local configuration file `poetry.toml`).
* `--migrate`: Migrate outdated configuration settings.

## debug

The `debug` command groups subcommands that are useful for, as the name suggests, debugging issues you might have
when using Poetry with your projects.

### debug info

The `debug info` command shows debug information about Poetry and your project's virtual environment.

### debug resolve

The `debug resolve` command helps when debugging dependency resolution issues. The command attempts to resolve your
dependencies and list the chosen packages and versions.

### debug tags

The `debug tags` command is useful when you want to see the supported packaging tags for your project's active
virtual environment. This is useful when Poetry cannot install any known binary distributions for a dependency.

## env

The `env` command groups subcommands to interact with the virtualenvs
associated with a specific project.

See [Managing environments]({{< relref "managing-environments" >}}) for more information about these commands.

### env activate

The `env activate` command prints the command to activate a virtual environment in your current shell.

{{% note %}}
This command does not activate the virtual environment, but only displays the activation command, for more information
on how to use this command see [here]({{< relref "managing-environments#activating-the-environment" >}}).
{{% /note %}}

### env info

The `env info` command displays information about the current environment.

#### Options

* `--path (-p)`: Only display the environment's path.
* `--executable (-e)`: Only display the environment's python executable path.

### env list

The `env list` command lists all virtualenvs associated with the current project.

#### Options

* `--full-path`: Output the full paths of the virtualenvs.

### env remove

The `env remove` command removes virtual environments associated with the project. You can specify multiple Python
executables or virtual environment names to remove all matching ones. Alternatively, you can remove all associated
virtual environments using the `--all` option.

{{% note %}}
If `virtualenvs.in-project` config is set to `true`, no argument or option is required. Your in project virtual environment is removed.
{{% /note %}}

#### Arguments

* `python`: The python executables associated with, or names of the virtual environments which are to be removed. Can be specified multiple times.

#### Options

* `--all`: Remove all managed virtual environments associated with the project.

### env use

The `env use` command activates or creates a new virtualenv for the current project.

#### Arguments

* `python`: The python executable to use. This can be a version number (if not on Windows) or a path to the python binary.

## export

{{% warning %}}
This command is provided by the [Export Poetry Plugin](https://github.com/python-poetry/poetry-plugin-export).
The plugin is no longer installed by default with Poetry 2.0.

See [Using plugins]({{< relref "plugins#using-plugins" >}}) for information on how to install a plugin.
As described in [Project plugins]({{< relref "plugins#project-plugins" >}}),
you can also define in your `pyproject.toml` that the plugin is required for the development of your project:

```toml
[tool.poetry.requires-plugins]
poetry-plugin-export = ">=1.8"
```
{{% /warning %}}

{{% note %}}
The `export` command is also available as a pre-commit hook.
See [pre-commit hooks]({{< relref "pre-commit-hooks#poetry-export" >}}) for more information.
{{% /note %}}

## help

The `help` command displays global help, or help for a specific command.

To display global help:

```bash
poetry help
```

To display help for a specific command, for instance `show`:

```bash
poetry help show
```

{{% note %}}
The `--help` option can also be passed to any command to get help for a specific command.

For instance:

```bash
poetry show --help
```
{{% /note %}}

## init

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
* `--python` Compatible Python versions.
* `--dependency`: Package to require with a version constraint. Should be in format `foo:1.0.0`.
* `--dev-dependency`: Development requirements, see `--dependency`.

## install

The `install` command reads the `pyproject.toml` file from the current project,
resolves the dependencies, and installs them.

{{% note %}}
Normally, you should prefer `poetry sync` to `poetry install` to avoid untracked outdated packages.
However, if you have set `virtualenvs.create = false` to install dependencies into your system environment,
which is discouraged, or `virtualenvs.options.system-site-packages = true` to make
system site-packages available in your virtual environment, you should use `poetry install`
because `poetry sync` will normally not work well in these cases.
{{% /note %}}

```bash
poetry install
```

If there is a `poetry.lock` file in the current directory,
it will use the exact versions from there instead of resolving them.
This ensures that everyone using the library will get the same versions of the dependencies.

If there is no `poetry.lock` file, Poetry will create one after dependency resolution.

If you want to exclude one or more dependency groups for the installation, you can use
the `--without` option.

```bash
poetry install --without test,docs
```

You can also select optional dependency groups with the `--with` option.

```bash
poetry install --with test,docs
```

To install all dependency groups including the optional groups, use the ``--all-groups`` flag.

```bash
poetry install --all-groups
```

It's also possible to only install specific dependency groups by using the `only` option.

```bash
poetry install --only test,docs
```

To only install the project itself with no dependencies, use the `--only-root` flag.

```bash
poetry install --only-root
```

See [Dependency groups]({{< relref "managing-dependencies#dependency-groups" >}}) for more information
about dependency groups.

You can also specify the extras you want installed
by passing the `-E|--extras` option (See [Extras]({{< relref "pyproject#extras" >}}) for more info).
Pass `--all-extras` to install all defined extras for a project.

```bash
poetry install --extras "mysql pgsql"
poetry install -E mysql -E pgsql
poetry install --all-extras
```

Any extras not specified will be kept but not installed:

```bash
poetry install --extras "A B"  # C is kept if already installed
```

If you want to remove unspecified extras, use the `sync` command.

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

Similar to `--no-root` you can use `--no-directory` to skip directory path dependencies:

```bash
poetry install --no-directory
```

This is mainly useful for caching in CI or when building Docker images. See the [FAQ entry]({{< relref "faq#poetry-busts-my-docker-cache-because-it-requires-me-to-copy-my-source-files-in-before-installing-3rd-party-dependencies" >}}) for more information on this option.

By default `poetry` does not compile Python source files to bytecode during installation.
This speeds up the installation process, but the first execution may take a little more
time because Python then compiles source files to bytecode automatically.
If you want to compile source files to bytecode during installation,
you can use the `--compile` option:

```bash
poetry install --compile
```

#### Options

* `--without`: The dependency groups to ignore.
* `--with`: The optional dependency groups to include.
* `--only`: The only dependency groups to include.
* `--only-root`: Install only the root project, exclude all dependencies.
* `--sync`: Synchronize the environment with the locked packages and the specified groups. (**Deprecated**, use `poetry sync` instead)
* `--no-root`: Do not install the root package (your project).
* `--no-directory`: Skip all directory path dependencies (including transitive ones).
* `--dry-run`: Output the operations but do not execute anything (implicitly enables `--verbose`).
* `--extras (-E)`: Features to install (multiple values allowed).
* `--all-extras`: Install all extra features (conflicts with `--extras`).
* `--all-groups`: Install dependencies from all groups (conflicts with `--only`, `--with`, and `--without`).
* `--compile`: Compile Python source files to bytecode.

{{% note %}}
When `--only` is specified, `--with` and `--without` options are ignored.
{{% /note %}}

## list

The `list` command displays all the available Poetry commands.

```bash
poetry list
```

## lock

This command locks (without installing) the dependencies specified in `pyproject.toml`.

{{% note %}}
By default, packages that have already been added to the lock file before will not be updated.
To update all dependencies to the latest available compatible versions, use `poetry update --lock`
or `poetry lock --regenerate`, which normally produce the same result.
This command is also available as a pre-commit hook. See [pre-commit hooks]({{< relref "pre-commit-hooks#poetry-lock">}}) for more information.
{{% /note %}}

```bash
poetry lock
```

#### Options

* `--regenerate`: Ignore existing lock file and overwrite it with a new lock file created from scratch.

## new

This command will help you kickstart your new Python project by creating a new Poetry project. By default, a `src`
layout is chosen.

```bash
poetry new my-package
```

will create a folder as follows:

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

If you want to name your project differently than the folder, you can pass
the `--name` option:

```bash
poetry new my-folder --name my-package
```

If you want to use a `flat` project layout, you can use the `--flat` option:

```bash
poetry new --flat my-package
```

That will create a folder structure as follows:

```text
my-package
├── pyproject.toml
├── README.md
├── my_package
│   └── __init__.py
└── tests
    └── __init__.py
```

{{% note %}}
For an overview of the differences between `flat` and `src` layouts, please see
[here](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/).
{{% /note %}}

The `--name` option is smart enough to detect namespace packages and create
the required structure for you.

```bash
poetry new --name my.package my-package
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

#### Options

* `--interactive (-i)`: Allow interactive specification of project configuration.
* `--name`: Set the resulting package name.
* `--flat`: Use the flat layout for the project.
* `--readme`: Specify the readme file extension. Default is `md`. If you intend to publish to PyPI
  keep the [recommendations for a PyPI-friendly README](https://packaging.python.org/en/latest/guides/making-a-pypi-friendly-readme/)
  in mind.
* `--description`: Description of the package.
* `--author`: Author of the package.
* `--python` Compatible Python versions.
* `--dependency`: Package to require with a version constraint. Should be in format `foo:1.0.0`.
* `--dev-dependency`: Development requirements, see `--dependency`.

## publish

This command publishes the package, previously built with the [`build`](#build) command, to the remote repository.

It will automatically register the package before uploading if this is the first time it is submitted.

```bash
poetry publish
```

It can also build the package if you pass it the `--build` option.

{{% note %}}
See [Publishable Repositories]({{< relref "repositories/#publishable-repositories" >}}) for more information on how to configure and use publishable repositories.
{{% /note %}}

#### Options

* `--repository (-r)`: The repository to register the package to (default: `pypi`).
Should match a repository name set by the [`config`](#config) command.
* `--username (-u)`: The username to access the repository.
* `--password (-p)`: The password to access the repository.
* `--cert`: Certificate authority to access the repository.
* `--client-cert`: Client certificate to access the repository.
* `--dist-dir`: Dist directory where built artifact are stored. Default is `dist`.
* `--build`: Build the package before publishing.
* `--dry-run`: Perform all actions except upload the package.
* `--skip-existing`: Ignore errors from files already existing in the repository.

{{% note %}}
See [Configuring Credentials]({{< relref "repositories/#configuring-credentials" >}}) for more information on how to configure credentials.
{{% /note %}}

## python

The `python` namespace groups subcommands to manage Python versions.

{{% warning %}}
This is an experimental feature, and can change behaviour in upcoming releases.
{{% /warning %}}

*Introduced in 2.1.0*

### python install

The `python install` command installs the specified Python version from the Python Standalone Builds project.

```bash
poetry python install <PYTHON_VERSION>
```

#### Options

* `--clean`: Clean up installation if check fails.
* `--free-threaded`: Use free-threaded version if available.
* `--implementation`: Python implementation to use. (cpython, pypy)
* `--reinstall`: Reinstall if installation already exists.

### python list

The `python list` command shows Python versions available in the environment. This includes both installed and
discovered System managed and Poetry managed installations.

```bash
poetry python list
```
#### Options
* `--all`: List all versions, including those available for download.
* `--implementation`: Python implementation to search for.
* `--managed`: List only Poetry managed Python versions.

### python remove

The `python remove` command removes the specified Python version if managed by Poetry.

```bash
poetry python remove <PYTHON_VERSION>
```

#### Options

* `--implementation`: Python implementation to use. (cpython, pypy)

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

#### Options

* `--group (-G)`: The group to remove the dependency from.
* `--dev (-D)`: Removes a package from the development dependencies. (shortcut for `-G dev`)
* `--dry-run` : Outputs the operations but will not execute anything (implicitly enables `--verbose`).
* `--lock`: Do not perform operations (only update the lockfile).

## run

The `run` command executes the given command inside the project's virtualenv.

```bash
poetry run python -V
```

It can also execute one of the scripts defined in `pyproject.toml`.

So, if you have a script defined like this:

{{< tabs tabTotal="2" tabID1="script-project" tabID2=script-poetry" tabName1="[project]" tabName2="[tool.poetry]">}}

{{< tab tabID="script-project" >}}
```toml
[project]
# ...
[project.scripts]
my-script = "my_module:main"
```
{{< /tab >}}

{{< tab tabID="script-poetry" >}}
```toml
[tool.poetry.scripts]
my-script = "my_module:main"
```
{{< /tab >}}
{{< /tabs >}}

You can execute it like so:

```bash
poetry run my-script
```

Note that this command has no option.

## search

This command searches for packages on a remote index.

```bash
poetry search requests pendulum
```

{{% note %}}
PyPI no longer allows for the search of packages without a browser. Please use https://pypi.org/search
(via a browser) instead.

For more information please see [warehouse documentation](https://warehouse.pypa.io/api-reference/xml-rpc.html#deprecated-methods)
and this [discussion](https://discuss.python.org/t/fastly-interfering-with-pypi-search/73597/6).
{{% /note %}}

## self

The `self` namespace groups subcommands to manage the Poetry installation itself.

{{% note %}}
Use of these commands will create the required `pyproject.toml` and `poetry.lock` files in your
[configuration directory]({{< relref "configuration" >}}).
{{% /note %}}

{{% warning %}}
Especially on Windows, `self` commands that update or remove packages may be problematic
so that other methods for installing plugins and updating Poetry are recommended.
See [Using plugins]({{< relref "plugins#using-plugins" >}}) and
[Installing Poetry]({{< relref "docs#installation" >}}) for more information.
{{% /warning %}}

### self add

The `self add` command installs Poetry plugins and make them available at runtime. Additionally, it can
also be used to upgrade Poetry's own dependencies or inject additional packages into the runtime
environment

{{% note %}}
The `self add` command works exactly like the [`add` command](#add). However, is different in that the packages
managed are for Poetry's runtime environment.

The package specification formats supported by the `self add` command are the same as the ones supported
by the [`add` command](#add).
{{% /note %}}

For example, to install the `poetry-plugin-export` plugin, you can run:

```bash
poetry self add poetry-plugin-export
```

To update to the latest `poetry-core` version, you can run:

```bash
poetry self add poetry-core@latest
```

To add a keyring provider `artifacts-keyring`, you can run:

```bash
poetry self add artifacts-keyring
```

#### Options

* `--editable (-e)`: Add vcs/path dependencies as editable.
* `--extras (-E)`: Extras to activate for the dependency. (multiple values allowed)
* `--allow-prereleases`: Accept prereleases.
* `--source`: Name of the source to use to install the package.
* `--dry-run`: Output the operations but do not execute anything (implicitly enables `--verbose`).

### self install

The `self install` command ensures all additional packages specified are installed in the current
runtime environment.

{{% note %}}
The `self install` command works similar to the [`install` command](#install). However,
it is different in that the packages managed are for Poetry's runtime environment.
{{% /note %}}

```bash
poetry self install
```

#### Options

* `--sync`: Synchronize the environment with the locked packages and the specified groups. (**Deprecated**, use `poetry self sync` instead)
* `--dry-run`: Output the operations but do not execute anything (implicitly enables `--verbose`).

### self lock

The `self lock` command reads this Poetry installation's system `pyproject.toml` file. The system
dependencies are locked in the corresponding `poetry.lock` file.

```bash
poetry self lock
```

#### Options

* `--regenerate`: Ignore existing lock file and overwrite it with a new lock file created from scratch.

### self remove

The `self remove` command removes an installed addon package.

```bash
poetry self remove poetry-plugin-export
```

#### Options

* `--dry-run`: Outputs the operations but will not execute anything (implicitly enables `--verbose`).

### self show

The `self show` command behaves similar to the show command, but
working within Poetry's runtime environment. This lists all packages installed within
the Poetry install environment.

To show only additional packages that have been added via self add and their
dependencies use `self show --addons`.

```bash
poetry self show
```

#### Options

* `--addons`: List only add-on packages installed.
* `--tree`: List the dependencies as a tree.
* `--latest (-l)`: Show the latest version.
* `--outdated (-o)`: Show the latest version but only for packages that are outdated.

### self show plugins

The `self show plugins` command lists all the currently installed plugins.

```bash
poetry self show plugins
```

### self sync

The `self sync` command ensures all additional (and no other) packages specified
are installed in the current runtime environment.

{{% note %}}
The `self sync` command works similar to the [`sync` command](#sync). However,
it is different in that the packages managed are for Poetry's runtime environment.
{{% /note %}}

```bash
poetry self sync
```

#### Options

* `--dry-run`: Output the operations but do not execute anything (implicitly enables `--verbose`).

### self update

The `self update` command updates Poetry version in its current runtime environment.

{{% note %}}
The `self update` command works exactly like the [`update` command](#update). However,
is different in that the packages managed are for Poetry's runtime environment.
{{% /note %}}

```bash
poetry self update
```

#### Options

* `--preview`: Allow the installation of pre-release versions.
* `--dry-run`: Output the operations but do not execute anything (implicitly enables `--verbose`).

## shell

The `shell` command was moved to a plugin: [`poetry-plugin-shell`](https://github.com/python-poetry/poetry-plugin-shell)

## show

To list all the available packages, you can use the `show` command.

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
 - calendar requires >=1.4.0
```

#### Options

* `--without`: The dependency groups to ignore.
* `--why`: When showing the full list, or a `--tree` for a single package, display whether they are a direct dependency or required by other packages.
* `--with`: The optional dependency groups to include.
* `--only`: The only dependency groups to include.
* `--tree`: List the dependencies as a tree.
* `--latest (-l)`: Show the latest version.
* `--outdated (-o)`: Show the latest version but only for packages that are outdated.
* `--all (-a)`: Show all packages (even those not compatible with current system).
* `--top-level (-T)`: Only show explicitly defined packages.
* `--no-truncate`: Do not truncate the output based on the terminal width.

{{% note %}}
When `--only` is specified, `--with` and `--without` options are ignored.
{{% /note %}}

## source

The `source` namespace groups subcommands to manage repository sources for a Poetry project.

### source add

The `source add` command adds source configuration to the project.

For example, to add the `pypi-test` source, you can run:

```bash
poetry source add --priority supplemental pypi-test https://test.pypi.org/simple/
```

You cannot use the name `pypi` for a custom repository as it is reserved for use by
the default PyPI source. However, you can set the priority of PyPI:

```bash
poetry source add --priority=explicit pypi
```

#### Options

* `--priority`: Set the priority of this source. Accepted values are: [`primary`]({{< relref "repositories#primary-package-sources" >}}), [`supplemental`]({{< relref "repositories#supplemental-package-sources" >}}), and [`explicit`]({{< relref "repositories#explicit-package-sources" >}}). Refer to the dedicated sections in [Repositories]({{< relref "repositories" >}}) for more information.

### source show

The `source show` command displays information on all configured sources for the project.

```bash
poetry source show
```

Optionally, you can show information of one or more sources by specifying their names.

```bash
poetry source show pypi-test
```

{{% note %}}
This command will only show sources configured via the `pyproject.toml`
and does not include the implicit default PyPI.
{{% /note %}}

### source remove

The `source remove` command removes a configured source from your `pyproject.toml`.

```bash
poetry source remove pypi-test
```

## sync

The `sync` command makes sure that the project's environment is in sync with the `poetry.lock` file.
It is similar to `poetry install` but it additionally removes packages that are not tracked in the lock file.

```bash
poetry sync
```

If there is a `poetry.lock` file in the current directory,
it will use the exact versions from there instead of resolving them.
This ensures that everyone using the library will get the same versions of the dependencies.

If there is no `poetry.lock` file, Poetry will create one after dependency resolution.

If you want to exclude one or more dependency groups for the installation, you can use
the `--without` option.

```bash
poetry sync --without test,docs
```

You can also select optional dependency groups with the `--with` option.

```bash
poetry sync --with test,docs
```

To install all dependency groups including the optional groups, use the ``--all-groups`` flag.

```bash
poetry sync --all-groups
```

It's also possible to only install specific dependency groups by using the `only` option.

```bash
poetry sync --only test,docs
```

To only install the project itself with no dependencies, use the `--only-root` flag.

```bash
poetry sync --only-root
```

See [Dependency groups]({{< relref "managing-dependencies#dependency-groups" >}}) for more information
about dependency groups.

You can also specify the extras you want installed
by passing the `-E|--extras` option (See [Extras]({{< relref "pyproject#extras" >}}) for more info).
Pass `--all-extras` to install all defined extras for a project.

```bash
poetry sync --extras "mysql pgsql"
poetry sync -E mysql -E pgsql
poetry sync --all-extras
```

Any extras not specified will always be removed.

```bash
poetry sync --extras "A B"  # C is removed
```

By default `poetry` will install your project's package every time you run `sync`:

```bash
$ poetry sync
Installing dependencies from lock file

No dependencies to install or update

  - Installing <your-package-name> (x.x.x)
```

If you want to skip this installation, use the `--no-root` option.

```bash
poetry sync --no-root
```

Similar to `--no-root` you can use `--no-directory` to skip directory path dependencies:

```bash
poetry sync --no-directory
```

This is mainly useful for caching in CI or when building Docker images. See the [FAQ entry]({{< relref "faq#poetry-busts-my-docker-cache-because-it-requires-me-to-copy-my-source-files-in-before-installing-3rd-party-dependencies" >}}) for more information on this option.

By default `poetry` does not compile Python source files to bytecode during installation.
This speeds up the installation process, but the first execution may take a little more
time because Python then compiles source files to bytecode automatically.
If you want to compile source files to bytecode during installation,
you can use the `--compile` option:

```bash
poetry sync --compile
```

#### Options

* `--without`: The dependency groups to ignore.
* `--with`: The optional dependency groups to include.
* `--only`: The only dependency groups to include.
* `--only-root`: Install only the root project, exclude all dependencies.
* `--no-root`: Do not install the root package (your project).
* `--no-directory`: Skip all directory path dependencies (including transitive ones).
* `--dry-run`: Output the operations but do not execute anything (implicitly enables `--verbose`).
* `--extras (-E)`: Features to install (multiple values allowed).
* `--all-extras`: Install all extra features (conflicts with `--extras`).
* `--all-groups`: Install dependencies from all groups (conflicts with `--only`, `--with`, and `--without`).
* `--compile`: Compile Python source files to bytecode.

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

Note that this will not update versions for dependencies outside their
[version constraints]({{< relref "dependency-specification#version-constraints" >}})
specified in the `pyproject.toml` file.
In other terms, `poetry update foo` will be a no-op if the version constraint
specified for `foo` is `~2.3` or `2.3` and `2.4` is available.
In order for `foo` to be updated, you must update the constraint, for example `^2.3`.
You can do this using the `add` command.

#### Options

* `--without`: The dependency groups to ignore.
* `--with`: The optional dependency groups to include.
* `--only`: The only dependency groups to include.
* `--dry-run` : Outputs the operations but will not execute anything (implicitly enables `--verbose`).
* `--lock` : Do not perform install (only update the lockfile).
* `--sync`: Synchronize the environment with the locked packages and the specified groups.

{{% note %}}
When `--only` is specified, `--with` and `--without` options are ignored.
{{% /note %}}

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

The option `--next-phase` allows the increment of prerelease phase versions.

| rule                    | before   | after    |
|-------------------------|----------|----------|
| prerelease --next-phase | 1.0.3a0  | 1.0.3b0  |
| prerelease --next-phase | 1.0.3b0  | 1.0.3rc0 |
| prerelease --next-phase | 1.0.3rc0 | 1.0.3    |

#### Options

* `--next-phase`: Increment the phase of the current version.
* `--short (-s)`: Output the version number only.
* `--dry-run`: Do not update pyproject.toml file.
