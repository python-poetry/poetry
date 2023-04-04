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

## Dependency groups

Poetry provides a way to **organize** your dependencies by **groups**. For instance, you might have
dependencies that are only needed to test your project or to build the documentation.

To declare a new dependency group, use a `tool.poetry.group.<group>` section
where `<group>` is the name of your dependency group (for instance, `test`):

```toml
[tool.poetry.group.test]  # This part can be left out

[tool.poetry.group.test.dependencies]
pytest = "^6.0.0"
pytest-mock = "*"
```

{{% note %}}
All dependencies **must be compatible with each other** across groups since they will
be resolved regardless of whether they are required for installation or not (see [Installing group dependencies]({{< relref "#installing-group-dependencies" >}})).

Think of dependency groups as **labels** associated with your dependencies: they don't have any bearings
on whether their dependencies will be resolved and installed **by default**, they are simply a way to organize
the dependencies logically.
{{% /note %}}

{{% note %}}
The dependencies declared in `tool.poetry.dependencies` are part of an implicit `main` group.

```toml
[tool.poetry.dependencies]  # main dependency group
httpx = "*"
pendulum = "*"

[tool.poetry.group.test.dependencies]
pytest = "^6.0.0"
pytest-mock = "*"
```
{{% /note %}}

{{% note %}}
Dependency groups, other than the implicit `main` group, must only contain dependencies you need in your development
process. Installing them is only possible by using Poetry.

To declare a set of dependencies, which add additional functionality to the project during runtime,
use [extras]({{< relref "pyproject#extras" >}}) instead. Extras can be installed by the end user using `pip`.
{{% /note %}}

{{% note %}}
**A note about defining a `dev` dependencies group**

The proper way to define a `dev` dependencies group since Poetry 1.2.0 is the following:

```toml
[tool.poetry.group.dev.dependencies]
pytest = "^6.0.0"
pytest-mock = "*"
```

This group notation is preferred since Poetry 1.2.0 and not usable in earlier versions.
For backwards compatibility with older versions of Poetry,
any dependency declared in the `dev-dependencies` section will automatically be added to the `dev` group.
So the above and following notations are equivalent:

```toml
# Poetry pre-1.2.x style, understood by Poetry 1.0–1.2
[tool.poetry.dev-dependencies]
pytest = "^6.0.0"
pytest-mock = "*"
```

Poetry will slowly transition away from the `dev-dependencies` notation which will soon be deprecated,
so it's advised to migrate your existing development dependencies to the new `group` notation.
{{% /note %}}

### Optional groups

A dependency group can be declared as optional. This makes sense when you have
a group of dependencies that are only required in a particular environment or for
a specific purpose.

```toml
[tool.poetry.group.docs]
optional = true

[tool.poetry.group.docs.dependencies]
mkdocs = "*"
```

Optional groups can be installed in addition to the **default** dependencies by using the `--with`
option of the [`install`]({{< relref "cli#install" >}}) command.

```bash
poetry install --with docs
```

{{% warning %}}
Optional group dependencies will **still** be resolved alongside other dependencies, so
special care should be taken to ensure they are compatible with each other.
{{% /warning %}}

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
The default set of dependencies for a project includes the implicit `main` group defined in
`tool.poetry.dependencies` as well as all groups that are not explicitly marked as an
[optional group]({{< relref "#optional-groups" >}}).
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

This is done by using the `--sync` option of the `install` command:

```bash
poetry install --sync
```

The `--sync` option can be combined with any [dependency groups]({{< relref "#dependency-groups" >}}) related options
to synchronize the environment with specific groups. Note that extras are separate.  Any
extras not selected for install are always removed, regardless of `--sync`.

```bash
poetry install --without dev --sync
poetry install --with docs --sync
poetry install --only dev
```

{{% note %}}
The `--sync` option replaces the `--remove-untracked` option which is now deprecated.
{{% /note %}}

## Layering optional groups

When you omit the `--sync` option, you can install any subset of optional groups without removing
those that are already installed.  This is very useful, for example, in multi-stage
Docker builds, where you run `poetry install` multiple times in different build stages.
