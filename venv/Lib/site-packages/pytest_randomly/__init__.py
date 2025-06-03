from __future__ import annotations

import argparse
import hashlib
import random
import sys
from itertools import groupby
from types import ModuleType
from typing import Any
from typing import Callable
from typing import TypeVar

from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.nodes import Item
from pytest import Collector
from pytest import fixture
from pytest import hookimpl

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

try:
    import xdist
except ImportError:  # pragma: no cover
    xdist = None

# factory-boy
try:
    from factory.random import set_random_state as factory_set_random_state

    have_factory_boy = True
except ImportError:  # pragma: no cover
    # old versions
    try:
        from factory.fuzzy import set_random_state as factory_set_random_state

        have_factory_boy = True
    except ImportError:
        have_factory_boy = False

# faker
try:
    from faker.generator import random as faker_random

    have_faker = True
except ImportError:  # pragma: no cover
    have_faker = False

# model_bakery
try:
    from model_bakery.random_gen import baker_random

    have_model_bakery = True
except ImportError:  # pragma: no cover
    have_model_bakery = False

# numpy
try:
    from numpy import random as np_random

    have_numpy = True
except ImportError:  # pragma: no cover
    have_numpy = False


default_seed = random.Random().getrandbits(32)


def seed_type(string: str) -> str | int:
    if string in ("default", "last"):
        return string
    try:
        return int(string)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"{repr(string)} is not an integer or the string 'last'"
        )


def pytest_addoption(parser: Parser) -> None:
    group = parser.getgroup("randomly", "pytest-randomly")
    group._addoption(
        "--randomly-seed",
        action="store",
        dest="randomly_seed",
        default="default",
        type=seed_type,
        help="""Set the seed that pytest-randomly uses (int), or pass the
                special value 'last' to reuse the seed from the previous run.
                Default behaviour: use random.Random().getrandbits(32), so the seed is
                different on each run.""",
    )
    group._addoption(
        "--randomly-dont-reset-seed",
        action="store_false",
        dest="randomly_reset_seed",
        default=True,
        help="""Stop pytest-randomly from resetting random.seed() at the
                start of every test context (e.g. TestCase) and individual
                test.""",
    )
    group._addoption(
        "--randomly-dont-reorganize",
        action="store_false",
        dest="randomly_reorganize",
        default=True,
        help="Stop pytest-randomly from randomly reorganizing the test order.",
    )


def pytest_configure(config: Config) -> None:
    if config.pluginmanager.hasplugin("xdist"):
        config.pluginmanager.register(XdistHooks())

    seed_value = config.getoption("randomly_seed")
    if seed_value == "last":
        assert hasattr(
            config, "cache"
        ), "The cacheprovider plugin is required to use 'last'"
        assert config.cache is not None
        seed = config.cache.get("randomly_seed", default_seed)
    elif seed_value == "default":
        if hasattr(config, "workerinput"):  # pragma: no cover
            # pytest-xdist: use seed generated on main.
            seed = config.workerinput["randomly_seed"]
        else:
            seed = default_seed
    else:
        seed = seed_value
    if hasattr(config, "cache"):
        assert config.cache is not None
        config.cache.set("randomly_seed", seed)
    config.option.randomly_seed = seed


class XdistHooks:
    # Hooks for xdist only, registered when needed in pytest_configure()
    # https://docs.pytest.org/en/latest/writing_plugins.html#optionally-using-hooks-from-3rd-party-plugins  # noqa: E501

    def pytest_configure_node(self, node: Item) -> None:
        seed = node.config.getoption("randomly_seed")
        node.workerinput["randomly_seed"] = seed  # type: ignore [attr-defined]


random_states: dict[int, tuple[Any, ...]] = {}
np_random_states: dict[int, Any] = {}


entrypoint_reseeds: list[Callable[[int], None]] | None = None


def _reseed(config: Config, offset: int = 0) -> int:
    global entrypoint_reseeds
    seed: int = config.getoption("randomly_seed") + offset
    if seed not in random_states:
        random.seed(seed)
        random_states[seed] = random.getstate()
    else:
        random.setstate(random_states[seed])

    if have_factory_boy:  # pragma: no branch
        factory_set_random_state(random_states[seed])

    if have_faker:  # pragma: no branch
        faker_random.setstate(random_states[seed])

    if have_model_bakery:  # pragma: no branch
        baker_random.setstate(random_states[seed])

    if have_numpy:  # pragma: no branch
        numpy_seed = _truncate_seed_for_numpy(seed)
        if numpy_seed not in np_random_states:
            np_random.seed(numpy_seed)
            np_random_states[numpy_seed] = np_random.get_state()
        else:
            np_random.set_state(np_random_states[numpy_seed])

    if entrypoint_reseeds is None:
        eps = entry_points(group="pytest_randomly.random_seeder")
        entrypoint_reseeds = [e.load() for e in eps]
    for reseed in entrypoint_reseeds:
        reseed(seed)

    return seed


def _truncate_seed_for_numpy(seed: int) -> int:
    seed = abs(seed)
    if seed <= 2**32 - 1:
        return seed

    seed_bytes = seed.to_bytes(seed.bit_length(), "big")
    return int.from_bytes(hashlib.sha512(seed_bytes).digest()[: 32 // 8], "big")


def pytest_report_header(config: Config) -> str:
    seed = config.getoption("randomly_seed")
    _reseed(config)
    return f"Using --randomly-seed={seed}"


def pytest_runtest_setup(item: Item) -> None:
    if item.config.getoption("randomly_reset_seed"):
        _reseed(item.config, -1)


def pytest_runtest_call(item: Item) -> None:
    if item.config.getoption("randomly_reset_seed"):
        _reseed(item.config)


def pytest_runtest_teardown(item: Item) -> None:
    if item.config.getoption("randomly_reset_seed"):
        _reseed(item.config, 1)


# pytest missing type hints for @hookimpl
@hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: Config, items: list[Item]) -> None:
    if not config.getoption("randomly_reorganize"):
        return

    seed = _reseed(config)

    modules_items: list[tuple[ModuleType | None, list[Item]]] = []
    for module, group in groupby(items, _get_module):
        modules_items.append(
            (
                module,
                _shuffle_by_class(list(group), seed),
            )
        )

    def _module_key(module_item: tuple[ModuleType | None, list[Item]]) -> bytes:
        module, _items = module_item
        if module is None:
            return _md5(f"{seed}::None")
        return _md5(f"{seed}::{module.__name__}")

    modules_items.sort(key=_module_key)

    items[:] = reduce_list_of_lists([subitems for module, subitems in modules_items])


def _get_module(item: Item) -> ModuleType | None:
    try:
        return getattr(item, "module", None)
    except (ImportError, Collector.CollectError):
        return None


def _shuffle_by_class(items: list[Item], seed: int) -> list[Item]:
    klasses_items: list[tuple[type[Any] | None, list[Item]]] = []

    def _item_key(item: Item) -> bytes:
        return _md5(f"{seed}::{item.nodeid}")

    for klass, group in groupby(items, _get_cls):
        klass_items = list(group)
        klass_items.sort(key=_item_key)
        klasses_items.append((klass, klass_items))

    def _cls_key(klass_items: tuple[type[Any] | None, list[Item]]) -> bytes:
        klass, items = klass_items
        if klass is None:
            return _md5(f"{seed}::None")
        return _md5(f"{seed}::{klass.__module__}.{klass.__qualname__}")

    klasses_items.sort(key=_cls_key)

    return reduce_list_of_lists([subitems for klass, subitems in klasses_items])


def _get_cls(item: Item) -> type[Any] | None:
    return getattr(item, "cls", None)


T = TypeVar("T")


def reduce_list_of_lists(lists: list[list[T]]) -> list[T]:
    new_list = []
    for list_ in lists:
        new_list.extend(list_)
    return new_list


def _md5(string: str) -> bytes:
    hasher = hashlib.md5(usedforsecurity=False)
    hasher.update(string.encode())
    return hasher.digest()


if have_faker:  # pragma: no branch

    @fixture(autouse=True)
    def faker_seed(pytestconfig: Config) -> int:
        result: int = pytestconfig.getoption("randomly_seed")
        return result
