---
draft: false
layout: single
menu:
  docs:
    weight: 11
title: Managing dependencies
type: docs
---


# Managing dependencies

Poetry supports specifying main dependencies in the [`project.dependencies`]({{< relref "pyproject#dependencies" >}}) section of your `pyproject.toml`
according to PEP 621. For legacy reasons and to define additional information that are only used by Poetry
the [`tool.poetry.dependencies`]({{< relref "pyproject#dependencies-and-dependency-groups" >}}) sections can be used.

See [Dependency specification]({{< relref "dependency-specification" >}}) for more information.

## Dependency groups

Poetry provides a way to **organize** your dependencies by **groups**.

The dependencies declared in `project.dependencies` respectively `tool.poetry.dependencies`
are part of an implicit `main` group. Those dependencies are required by your project during runtime.

Besides the `main` dependencies, you might have dependencies that are only needed to test your project
or to build the documentation.

To declare a new dependency group, use a `dependency-groups` section according to PEP 735 or
a `tool.poetry.group.<group>` section where `<group>` is the name of your dependency group (for instance, `test`):

{{< tabs tabTotal="2" tabID1="group-pep735" tabID2="group-poetry" tabName1="[dependency-groups]" tabName2="[tool.poetry]">}}

{{< tab tabID="group-pep735" >}}
```toml
[dependency-groups]
test = [
    "pytest (>=6.0.0,<7.0.0)",
    "pytest-mock",
]
```
{{< /tab >}}

{{< tab tabID="group-poetry" >}}
```toml
[tool.poetry.group.test.dependencies]
pytest = "^6.0.0"
pytest-mock = "*"
```
{{< /tab >}}
{{< /tabs >}}


{{% note %}}
All dependencies **must be compatible with each other** across groups since they will
be resolved regardless of whether they are required for installation or not (see [Installing group dependencies]({{< relref "#installing-group-dependencies" >}})).

Think of dependency groups as **labels** associated with your dependencies: they don't have any bearings
on whether their dependencies will be resolved and installed **by default**, they are simply a way to organize
the dependencies logically.
{{% /note %}}

{{% note %}}
Dependency groups, other than the implicit `main` group,
must only contain dependencies you need in your development process.
To declare a set of dependencies, which add additional functionality to the project
during runtime, use [extras]({{< relref "pyproject#extras" >}}) instead.
{{% /note %}}


### Optional groups

A dependency group can be declared as optional. This makes sense when you have
a group of dependencies that are only required in a particular environment or for
a specific purpose.

{{< tabs tabTotal="2" tabID1="group-optional-pep735" tabID2="group-optional-poetry" tabName1="[dependency-groups]" tabName2="[tool.poetry]">}}

{{< tab tabID="group-optional-pep735" >}}
```toml
[dependency-groups]
docs = [
    "mkdocs",
]

[tool.poetry.group.docs]
optional = true
```
{{< /tab >}}

{{< tab tabID="group-optional-poetry" >}}
```toml
[tool.poetry.group.docs]
optional = true

[tool.poetry.group.docs.dependencies]
mkdocs = "*"
```
{{< /tab >}}
{{< /tabs >}}



Optional groups can be installed in addition to the **default** dependencies by using the `--with`
option of the [`install`]({{< relref "cli#install" >}}) command.

```bash
poetry install --with docs
```

{{% warning %}}
Optional group dependencies will **still** be resolved alongside other dependencies, so
special care should be taken to ensure they are compatible with each other.
{{% /warning %}}

### Including dependencies from other groups

You can include dependencies from one group in another group.
This is useful when you want to aggregate dependencies from multiple groups into a single group.

{{< tabs tabTotal="2" tabID1="group-include-pep735" tabID2="group-include-poetry" tabName1="[dependency-groups]" tabName2="[tool.poetry]">}}

{{< tab tabID="group-include-pep735" >}}
```toml
[dependency-groups]
test = [
    "pytest (>=8.0.0,<9.0.0)",
]
lint = [
    "ruff (>=0.11.0,<0.12.0)",
]
dev = [
    { include-group = "test" },
    { include-group = "lint" },
    "tox",
]
```
{{< /tab >}}

{{< tab tabID="group-include-poetry" >}}
```toml
[tool.poetry.group.test.dependencies]
pytest = "^8.0.0"

[tool.poetry.group.lint.dependencies]
ruff = "^0.11"

[tool.poetry.group.dev]
include-groups = [
    "test",
    "lint",
]

[tool.poetry.group.dev.dependencies]
tox = "*"
```
{{< /tab >}}
{{< /tabs >}}

In this example, the `dev` group includes all dependencies from the `test` and `lint` groups.

### Adding a dependency to a group

The [`add`]({{< relref "cli#add" >}}) command is the preferred way to add dependencies
to a group. This is done by using the `--group (-G)` option.

```bash
poetry add pytest --group test
```

If the group does not already exist, it will be created automatically.

### Installing group dependencies

**By default**, dependencies across **all non-optional groups** will be installed when executing
`poetry install`.

{{% note %}}
The default set of dependencies for a project includes the implicit `main` group as well as all
groups that are not explicitly marked as an [optional group]({{< relref "#optional-groups" >}}).
{{% /note %}}

You can **exclude** one or more groups with the `--without` option:

```bash
poetry install --without test,docs
```

You can also opt in [optional groups]({{< relref "#optional-groups" >}}) by using the `--with` option:

```bash
poetry install --with docs
```

{{% warning %}}
When used together, `--without` takes precedence over `--with`. For example, the following command
will only install the dependencies specified in the optional `test` group.

```bash
poetry install --with test,docs --without docs
```
{{% /warning %}}

Finally, in some case you might want to install **only specific groups** of dependencies
without installing the default set of dependencies. For that purpose, you can use
the `--only` option.

```bash
poetry install --only docs
```

{{% note %}}
If you only want to install the project's runtime dependencies, you can do so with the
`--only main` notation:

```bash
poetry install --only main
```
{{% /note %}}

{{% note %}}
If you want to install the project root, and no other dependencies, you can use
the `--only-root` option.

```bash
poetry install --only-root
```
{{% /note %}}

### Removing dependencies from a group

The [`remove`]({{< relref "cli#remove" >}}) command supports a `--group` option
to remove packages from a specific group:

```bash
poetry remove mkdocs --group docs
```

## Synchronizing dependencies

Poetry supports what's called dependency synchronization. Dependency synchronization ensures
that the locked dependencies in the `poetry.lock` file are the only ones present
in the environment, removing anything that's not necessary.

This is done by using the `sync` command:

```bash
poetry sync
```

The `sync` command can be combined with any [dependency groups]({{< relref "#dependency-groups" >}}) related options
to synchronize the environment with specific groups. Note that extras are separate.
Any extras not selected for install are always removed.

```bash
poetry sync --without dev
poetry sync --with docs
poetry sync --only dev
```

## Layering optional groups

When using the `install` command without the `--sync` option, you can install any subset of optional groups without removing
those that are already installed.  This is very useful, for example, in multi-stage
Docker builds, where you run `poetry install` multiple times in different build stages.
