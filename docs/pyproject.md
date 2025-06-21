---
title: "The pyproject.toml file"
draft: false
type: docs
layout: single

menu:
  docs:
    weight: 90
---

# The `pyproject.toml` file

In package mode, the only required fields are `name` and `version`
(either in the `project` section or in the `tool.poetry` section).
Other fields are optional.
In non-package mode, the `name` and `version` fields are required
if using the `project` section.

{{% note %}}
Run `poetry check` to print warnings about deprecated fields.
{{% /note %}}


## The `project` section

The `project` section of the `pyproject.toml` file according to the
[specification of the PyPA](https://packaging.python.org/en/latest/specifications/pyproject-toml/#declaring-project-metadata-the-project-table).

### name

The name of the package. **Always required when the `project` section is specified**

This should be a valid name as defined by [PEP 508](https://peps.python.org/pep-0508/#names).


```toml
name = "my-package"
```

### version

The version of the package. **Always required when the `project` section is specified**

This should be a valid [PEP 440](https://peps.python.org/pep-0440/) string.

```toml
version = "0.1.0"
```

If you want to set the version dynamically via `poetry build --local-version`
or you are using a plugin, which sets the version dynamically, you should add `version`
to dynamic and define the base version in the `tool.poetry` section, for example:

```toml
[project]
name = "my-package"
dynamic = [ "version" ]

[tool.poetry]
version = "1.0"  # base version
```

### description

A short description of the package.

```toml
description = "A short description of the package."
```

### license

The license of the package.

The recommended notation for the most common licenses is (alphabetical):

* Apache-2.0
* BSD-2-Clause
* BSD-3-Clause
* BSD-4-Clause
* GPL-2.0-only
* GPL-2.0-or-later
* GPL-3.0-only
* GPL-3.0-or-later
* LGPL-2.1-only
* LGPL-2.1-or-later
* LGPL-3.0-only
* LGPL-3.0-or-later
* MIT

Optional, but it is highly recommended to supply this.
More identifiers are listed at the [SPDX Open Source License Registry](https://spdx.org/licenses/).

```toml
license = { text = "MIT" }
```
{{% note %}}
If your project is proprietary and does not use a specific license, you can set this value as `Proprietary`.
{{% /note %}}

You can also specify a license file. However, when doing this, the complete license text
will be added to the metadata and the License classifier cannot be determined
automatically so that you have to add it manually.

```toml
license = { file = "LICENSE" }
```

### readme

A path to the README file or the content.

```toml
readme = "README.md"
```

{{% note %}}
If you want to define multiple README files, you have to add `readme` to `dynamic`
and define them in the `tool.poetry` section.
{{% /note %}}

```toml
[project]
# ...
dynamic = [ "readme" ]

[tool.poetry]
# ...
readme = ["docs/README1.md", "docs/README2.md"]
```

### requires-python

The Python version requirements of the project.

```toml
requires-python = ">=3.8"
```

{{% note %}}
If you need an upper bound for locking, but do not want to define an upper bound
in your package metadata, you can omit the upper bound in the `requires-python` field
and add it in the `tool.poetry.dependencies` section.
{{% /note %}}

```toml
[project]
# ...
requires-python = ">=3.8"

[tool.poetry.dependencies]
python = ">=3.8,<4.0"
```

### authors

The authors of the package.

This is a list of authors and should contain at least one author.

```toml
authors = [
    { name = "Sébastien Eustace", email = "sebastien@eustace.io" },
]
```

### maintainers

The maintainers of the package.

This is a list of maintainers and should be distinct from authors.

```toml
maintainers = [
    { name = "John Smith", email = "johnsmith@example.org" },
    { name = "Jane Smith", email = "janesmith@example.org" },
]
```

### keywords

A list of keywords that the package is related to.

```toml
keywords = [ "packaging", "poetry" ]
```

### classifiers

A list of PyPI [trove classifiers](https://pypi.org/classifiers/) that describe the project.

```toml
classifiers = [
    "Topic :: Software Development :: Build Tools",
    "Topic :: Software Development :: Libraries :: Python Modules"
]
```

{{% warning %}}
Note that suitable classifiers based on your `python` requirement and `license`
are **not** automatically added for you if you define classifiers statically
in the `project` section.

If you want to enrich classifiers automatically, you should add `classifiers` to `dynamic`
and use the `tool.poetry` section instead.
{{% /warning %}}

```toml
[project]
# ...
dynamic = [ "classifiers" ]

[tool.poetry]
# ...
classifiers = [
    "Topic :: Software Development :: Build Tools",
    "Topic :: Software Development :: Libraries :: Python Modules"
]
```

### urls

The URLs of the project.

```toml
[project.urls]
homepage = "https://python-poetry.org/"
repository = "https://github.com/python-poetry/poetry"
documentation = "https://python-poetry.org/docs/"
"Bug Tracker" = "https://github.com/python-poetry/poetry/issues"
```

If you publish your package on PyPI, they will appear in the `Project Links` section.

### scripts

This section describes the console scripts that will be installed when installing the package.

```toml
[project.scripts]
my_package_cli = 'my_package.console:run'
```

Here, we will have the `my_package_cli` script installed which will execute the `run` function in the `console` module in the `my_package` package.

{{% note %}}
When a script is added or updated, run `poetry install` to make them available in the project's virtualenv.
{{% /note %}}

{{% note %}}
To include a file as a script, use [`tool.poetry.scripts`]({{< relref "#scripts-1" >}}) instead.
{{% /note %}}

### gui-scripts

This section describes the GUI scripts that will be installed when installing the package.

```toml
[project.gui-scripts]
my_package_gui = 'my_package.gui:run'
```

Here, we will have the `my_package_gui` script installed which will execute the `run` function in the `gui` module in the `my_package` package.

{{% note %}}
When a script is added or updated, run `poetry install` to make them available in the project's virtualenv.
{{% /note %}}

### entry-points

Entry points can be used to define plugins for your package.

Poetry supports arbitrary plugins, which are exposed as the ecosystem-standard
[entry points](https://packaging.python.org/en/latest/specifications/entry-points/)
and discoverable using `importlib.metadata`.
This is similar to (and compatible with) the entry points feature of `setuptools`.
The syntax for registering a plugin is:

```toml
[project.entry-points] # Optional super table

[project.entry-points."A"]
B = "C:D"
```
Which are:

- `A` - type of the plugin, for example `poetry.plugin` or `flake8.extension`
- `B` - name of the plugin
- `C` - python module import path
- `D` - the entry point of the plugin (a function or class)

Example (from [`poetry-plugin-export`](http://github.com/python-poetry/poetry-plugin-export)):

```toml
[project.entry-points."poetry.application.plugin"]
export = "poetry_plugin_export.plugins:ExportApplicationPlugin"
```

### dependencies

The `dependencies` of the project.

```toml
dependencies = [
    "requests>=2.13.0",
]
```

These are the dependencies that will be declared when building an sdist or a wheel.

See [Dependency specification]({{< relref "dependency-specification" >}}) for more information
about the relation between `project.dependencies` and `tool.poetry.dependencies`.

### optional-dependencies

The optional dependencies of the project (also known as extras).

```toml
[project.optional-dependencies]
mysql = [ "mysqlclient>=1.3,<2.0" ]
pgsql = [ "psycopg2>=2.9,<3.0" ]
databases = [ "mysqlclient>=1.3,<2.0", "psycopg2>=2.9,<3.0" ]
```

{{% note %}}

You can enrich optional dependencies for locking in the `tool.poetry` section
analogous to `dependencies`.

{{% /note %}}


## The `tool.poetry` section

The `tool.poetry` section of the `pyproject.toml` file is composed of multiple sections.

### package-mode

Whether Poetry operates in package mode (default) or not.

See [basic usage]({{< relref "basic-usage#operating-modes" >}}) for more information.

```toml
package-mode = false
```

### name

**Deprecated**: Use `project.name` instead.

The name of the package. **Required in package mode if not defined in the project section**

This should be a valid name as defined by [PEP 508](https://peps.python.org/pep-0508/#names).


```toml
name = "my-package"
```

### version

{{% note %}}
If you do not want to set the version dynamically via `poetry build --local-version`
and you are not using a plugin, which sets the version dynamically,
prefer `project.version` over this setting.
{{% /note %}}

The version of the package. **Required in package mode if not defined in the project section**

This should be a valid [PEP 440](https://peps.python.org/pep-0440/) string.

```toml
version = "0.1.0"
```

{{% note %}}

If you would like to use semantic versioning for your project, please see
[here]({{< relref "libraries#versioning" >}}).

{{% /note %}}

### description

**Deprecated**: Use `project.description` instead.

A short description of the package.

```toml
description = "A short description of the package."
```

### license

**Deprecated**: Use `project.license` instead.

The license of the package.

The recommended notation for the most common licenses is (alphabetical):

* Apache-2.0
* BSD-2-Clause
* BSD-3-Clause
* BSD-4-Clause
* GPL-2.0-only
* GPL-2.0-or-later
* GPL-3.0-only
* GPL-3.0-or-later
* LGPL-2.1-only
* LGPL-2.1-or-later
* LGPL-3.0-only
* LGPL-3.0-or-later
* MIT

Optional, but it is highly recommended to supply this.
More identifiers are listed at the [SPDX Open Source License Registry](https://spdx.org/licenses/).

```toml
license = "MIT"
```
{{% note %}}
If your project is proprietary and does not use a specific licence, you can set this value as `Proprietary`.
{{% /note %}}

### authors

**Deprecated**: Use `project.authors` instead.

The authors of the package.

This is a list of authors and should contain at least one author. Authors must be in the form `name <email>`.

```toml
authors = [
    "Sébastien Eustace <sebastien@eustace.io>",
]
```

### maintainers

**Deprecated**: Use `project.maintainers` instead.

The maintainers of the package.

This is a list of maintainers and should be distinct from authors. Maintainers may contain an email and be in the form `name <email>`.

```toml
maintainers = [
    "John Smith <johnsmith@example.org>",
    "Jane Smith <janesmith@example.org>",
]
```

### readme

{{% note %}}
If you do not want to set multiple README files, prefer `project.readme` over this setting.
{{% /note %}}

A path, or list of paths corresponding to the README file(s) of the package.

The file(s) can be of any format, but if you intend to publish to PyPI keep the
[recommendations for a PyPI-friendly README](
https://packaging.python.org/en/latest/guides/making-a-pypi-friendly-readme/) in
mind. README paths are implicitly relative to `pyproject.toml`.

{{% note %}}
Whether paths are case-sensitive follows platform defaults, but it is recommended to keep cases.

To be specific, you can set `readme = "rEaDmE.mD"` for `README.md` on macOS and Windows, but Linux users can't `poetry install` after cloning your repo. This is because macOS and Windows are case-insensitive and case-preserving.
{{% /note %}}

The contents of the README file(s) are used to populate the [Description
field](https://packaging.python.org/en/latest/specifications/core-metadata/#description-optional)
of your distribution's metadata (similar to `long_description` in setuptools).
When multiple files are specified they are concatenated with newlines.

```toml
[tool.poetry]
# ...
readme = "README.md"
```

```toml
[tool.poetry]
# ...
readme = ["docs/README1.md", "docs/README2.md"]
```

### homepage

**Deprecated**: Use `project.urls` instead.

An URL to the website of the project.

```toml
homepage = "https://python-poetry.org/"
```

### repository

**Deprecated**: Use `project.urls` instead.

An URL to the repository of the project.

```toml
repository = "https://github.com/python-poetry/poetry"
```

### documentation

**Deprecated**: Use `project.urls` instead.

An URL to the documentation of the project.

```toml
documentation = "https://python-poetry.org/docs/"
```

### keywords

**Deprecated**: Use `project.keywords` instead.

A list of keywords that the package is related to.

```toml
keywords = ["packaging", "poetry"]
```

### classifiers

A list of PyPI [trove classifiers](https://pypi.org/classifiers/) that describe the project.

```toml
[tool.poetry]
# ...
classifiers = [
    "Topic :: Software Development :: Build Tools",
    "Topic :: Software Development :: Libraries :: Python Modules"
]
```

{{% note %}}
Note that Python classifiers are automatically added for you
and are determined by your `python` requirement.

The `license` property will also set the License classifier automatically.

If you do not want Poetry to automatically add suitable classifiers
based on the `python` requirement and `license` property,
use `project.classifiers` instead of this setting.
{{% /note %}}

### packages

A list of packages and modules to include in the final distribution.

If your project structure differs from the standard one supported by `poetry`,
you can specify the packages you want to include in the final distribution.

```toml
[tool.poetry]
# ...
packages = [
    { include = "my_package" },
    { include = "extra_package/**/*.py" },
]
```

If your package is stored inside a "lib" directory, you must specify it:

```toml
[tool.poetry]
# ...
packages = [
    { include = "my_package", from = "lib" },
]
```

The `to` parameter is designed to specify the relative destination path
where the package will be located upon installation. This allows for
greater control over the organization of packages within your project's structure.

```toml
[tool.poetry]
# ...
packages = [
    { include = "my_package", from = "lib", to = "target_package" },
]
```

If you want to restrict a package to a specific build format, you can specify
it by using `format`:

```toml
[tool.poetry]
# ...
packages = [
    { include = "my_package" },
    { include = "my_other_package", format = "sdist" },
]
```

From now on, only the `sdist` build archive will include the `my_other_package` package.

{{% note %}}
Using `packages` disables the package auto-detection feature meaning you have to
**explicitly** specify the "default" package.

For instance, if you have a package named `my_package` and you want to also include
another package named `extra_package`, you will need to specify `my_package` explicitly:

```toml
packages = [
    { include = "my_package" },
    { include = "extra_package" },
]
```
{{% /note %}}

{{% note %}}
Poetry is clever enough to detect Python subpackages.

Thus, you only have to specify the directory where your root package resides.
{{% /note %}}

### exclude and include

{{% note %}}
If you just want to include a package or module, which is not picked up automatically,
use [packages]({{< relref "#packages" >}}) instead of `include`.
{{% /note %}}

A list of patterns that will be excluded or included in the final package.

```toml
[tool.poetry]
# ...
exclude = ["my_package/excluded.py"]
include = ["CHANGELOG.md"]
```

You can explicitly specify to Poetry that a set of globs should be ignored or included for the purposes of packaging.
The globs specified in the exclude field identify a set of files that are not included when a package is built.
`include` has priority over `exclude`.

If a VCS is being used for a package, the exclude field will be seeded with the VCS’ ignore settings (`.gitignore` for git, for example).

{{% note %}}
Explicitly declaring entries in `include` will negate VCS' ignore settings.
{{% /note %}}

You can also specify the formats for which these patterns have to be included, as shown here:

```toml
[tool.poetry]
# ...
include = [
    { path = "tests", format = "sdist" },
    { path = "my_package/for_sdist_and_wheel.txt", format = ["sdist", "wheel"] }
]
```

If no format is specified, `include` defaults to only `sdist`.

In contrast, `exclude` defaults to both `sdist` and `wheel`.

{{% warning %}}
When a wheel is installed, its includes are unpacked straight into the `site-packages` directory.
Pay attention to include top level files and directories with common names like
`CHANGELOG.md`, `LICENSE`, `tests` or `docs` only in sdists and **not** in wheels.
{{% /warning %}}


### dependencies and dependency groups

Poetry is configured to look for dependencies on [PyPI](https://pypi.org) by default.
Only the name and a version string are required in this case.

```toml
[tool.poetry.dependencies]
requests = "^2.13.0"
```

If you want to use a [private repository]({{< relref "repositories#using-a-private-repository" >}}),
you can add it to your `pyproject.toml` file, like so:

```toml
[[tool.poetry.source]]
name = "private"
url = "http://example.com/simple"
```

If you have multiple repositories configured, you can explicitly tell poetry where to look for a specific package:

```toml
[tool.poetry.dependencies]
requests = { version = "^2.13.0", source = "private" }
```

You may also specify your project's compatible python versions in this section, instead of or in addition to `project.requires-python`.

```toml
[tool.poetry.dependencies]
python = "^3.7"
```

{{% note %}}
If you specify the compatible python versions in both `tool.poetry.dependencies` and in `project.requires-python`, then Poetry will use the information in `tool.poetry.dependencies` for locking, but the python versions must be a subset of those allowed by `project.requires-python`.

For example, the following is invalid and will result in an error, because versions `4.0` and greater are allowed by `tool.poetry.dependencies`, but not by `project.requires-python`.

```toml
[project]
# ...
requires-python = ">=3.8,<4.0"

[tool.poetry.dependencies]
python = ">=3.8" # not valid!
```
{{% /note %}}

You can organize your dependencies in [groups]({{< relref "managing-dependencies#dependency-groups" >}})
to manage them in a more granular way.

```toml
[tool.poetry.group.test.dependencies]
pytest = "*"

[tool.poetry.group.docs.dependencies]
mkdocs = "*"
```

See [Dependency groups]({{< relref "managing-dependencies#dependency-groups" >}}) for a more in-depth look
at how to manage dependency groups and [Dependency specification]({{< relref "dependency-specification" >}})
for more information on other keys and specifying version ranges.

### scripts

{{% note %}}
**Deprecated**: Use [`project.scripts`]({{< relref "#scripts" >}}) instead for `console` and `gui` scripts. Use
`[tool.poetry.scripts]` only for scripts of type `file`.
{{% /note %}}

This section describes the scripts or executables that will be installed when installing the package

```toml
[tool.poetry.scripts]
my_package_cli = 'my_package.console:run'
```

Here, we will have the `my_package_cli` script installed which will execute the `run` function in the `console` module in the `my_package` package.

{{% note %}}
When a script is added or updated, run `poetry install` to make them available in the project's virtualenv.
{{% /note %}}

```toml
[tool.poetry.scripts]
my_executable = { reference = "some_binary.exe", type = "file" }
```

This tells Poetry to include the specified file, relative to your project directory, in distribution builds. It will then be copied to the appropriate installation directory for your operating system when your package is installed.

* On Windows the file is placed in the `Scripts/` directory.
* On *nix system the file is placed in the `bin/` directory.

In its table form, the value of each script can contain a `reference` and `type`. The supported types are
`console` and `file`. When the value is a string, it is inferred to be a `console` script.

### extras

**Deprecated**: Use `project.optional-dependencies` instead.

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
psycopg2 = { version = "^2.9", optional = true }
mysqlclient = { version = "^1.3", optional = true }

[tool.poetry.extras]
mysql = ["mysqlclient"]
pgsql = ["psycopg2"]
databases = ["mysqlclient", "psycopg2"]
```

When installing packages with Poetry, you can specify extras by using the `-E|--extras` option:

```bash
poetry install --extras "mysql pgsql"
poetry install -E mysql -E pgsql
```

Any extras you don't specify will be removed. Note this behavior is different from
[optional dependency groups]({{< relref "managing-dependencies#optional-groups" >}}) not
selected for installation, e.g., those not specified via `install --with`.

You can install all extras with the `--all-extras` option:

```bash
poetry install --all-extras
```

{{% note %}}
Note that `install --extras` and the variations mentioned above (`--all-extras`, `--extras foo`, etc.) only work on dependencies defined in the current project. If you want to install extras defined by dependencies, you'll have to express that in the dependency itself:
```toml
[tool.poetry.dependencies]
pandas = {version="^2.2.1", extras=["computation", "performance"]}
```
```toml
[tool.poetry.group.dev.dependencies]
fastapi = {version="^0.92.0", extras=["all"]}
```
{{% /note %}}

When installing or specifying Poetry-built packages, the extras defined in this section can be activated
as described in [PEP 508](https://www.python.org/dev/peps/pep-0508/#extras).

For example, when installing the package using `pip`, the dependencies required by
the `databases` extra can be installed as shown below.

```bash
pip install awesome[databases]
```

{{% note %}}
The dependencies specified for each `extra` must already be defined as project dependencies.

Dependencies listed in [dependency groups]({{< relref "managing-dependencies#dependency-groups" >}}) cannot be specified as extras.
{{% /note %}}


### plugins

**Deprecated**: Use `project.entry-points` instead.

Poetry supports arbitrary plugins, which are exposed as the ecosystem-standard [entry points](https://packaging.python.org/en/latest/specifications/entry-points/) and discoverable using `importlib.metadata`. This is similar to (and compatible with) the entry points feature of `setuptools`.
The syntax for registering a plugin is:

```toml
[tool.poetry.plugins] # Optional super table

[tool.poetry.plugins."A"]
B = "C:D"
```
Which are:

- `A` - type of the plugin, for example `poetry.plugin` or `flake8.extension`
- `B` - name of the plugin
- `C` - python module import path
- `D` - the entry point of the plugin (a function or class)

Example (from [`poetry-plugin-export`](http://github.com/python-poetry/poetry-plugin-export)):

```toml
[tool.poetry.plugins."poetry.application.plugin"]
export = "poetry_plugin_export.plugins:ExportApplicationPlugin"
```

### urls

**Deprecated**: Use `project.urls` instead.

In addition to the basic urls (`homepage`, `repository` and `documentation`), you can specify
any custom url in the `urls` section.

```toml
[tool.poetry.urls]
"Bug Tracker" = "https://github.com/python-poetry/poetry/issues"
```

If you publish your package on PyPI, they will appear in the `Project Links` section.

### requires-poetry

A constraint for the Poetry version that is required for this project.
If you are using a Poetry version that is not allowed by this constraint,
an error will be raised.

```toml
[tool.poetry]
requires-poetry = ">=2.0"
```

### requires-plugins

In this section, you can specify that certain plugins are required for your project:

```toml
[tool.poetry.requires-plugins]
my-application-plugin = ">=1.0"
my-plugin = ">=1.0,<2.0"
```

See [Project plugins]({{< relref "plugins#project-plugins" >}}) for more information.

## Poetry and PEP-517

[PEP-517](https://www.python.org/dev/peps/pep-0517/) introduces a standard way
to define alternative build systems to build a Python project.

Poetry is compliant with PEP-517, by providing a lightweight core library,
so if you use Poetry to manage your Python project, you should reference
it in the `build-system` section of the `pyproject.toml` file like so:

```toml
[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

{{% note %}}
When using the `new` or `init` command this section will be automatically added.
{{% /note %}}

{{% note %}}
If your `pyproject.toml` file still references `poetry` directly as a build backend,
you should update it to reference `poetry-core` instead.
{{% /note %}}
