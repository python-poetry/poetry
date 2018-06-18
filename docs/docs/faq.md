# FAQ

## Why is the dependency resolution process slow?

While the dependency resolver at the heart of Poetry is highly optimized and
should be fast enough for most cases, sometimes, with some specific set of dependencies,
it can take time to find a valid solution.

This is due to the fact that not all libraries on PyPI have properly declared their metadata
and, as such, they are not available via the PyPI JSON API. At this point, Poetry has no choice
but downloading the packages and inspect them to get the necessary information. This is an expensive
operation, both in bandwidth and time, which is why it seems this is a long process.

At the moment there is not way around it.

!!!note

    Once Poetry has cached the releases' information, the dependency resolution process
    will be much faster.

## Why are unbound version constraints a bad idea?

A version constraint without an upper bound such as `*` or `>=3.4` will allow updates to any future version of the dependency.
This includes major versions breaking backward compatibility.

Once a release of your package is published, you cannot tweak its dependencies anymore in case a dependency breaks BC
- you have to do a new release but the previous one stays broken.

The only good alternative is to define an upper bound on your constraints,
which you can increase in a new release after testing that your package is compatible
with the new major version of your dependency.

For example instead of using `>=3.4` you should use `~3.4` which allows all versions `<4.0`.
The `^` operator works very well with libraries following [semantic versioning](https://semver.org).

## Is tox supported?

For now, you can use Poetry with [tox](https://tox.readthedocs.io/en/latest/) by using something similar to what is done in the [Pendulum](https://github.com/sdispater/pendulum/blob/master/tox.ini) package.

Minimal viable `tox.ini` configuration file looks like this:

```INI
[tox]
skipsdist = True
envlist = py27, py36

[testenv]
whitelist_externals = poetry
skip_install = true
commands =
    poetry install -v
    poetry run pytest tests/
```
