from __future__ import annotations

import functools
import logging
import os
import sys
import time

from concurrent.futures import wait
from concurrent.futures.thread import ThreadPoolExecutor
from typing import TYPE_CHECKING

import pytest

from poetry.utils.threading import AtomicCachedProperty
from poetry.utils.threading import atomic_cached_property


if TYPE_CHECKING:
    from collections.abc import Generator

    from pytest import LogCaptureFixture
    from pytest_mock import MockerFixture


WORKER_COUNT = (os.cpu_count() or 1) + 4
EXPECTED_VALUE = sum(range(1_00_000))
IS_PY_312 = (sys.version_info.major, sys.version_info.minor) >= (3, 12)


class Example:
    def __init__(self, value: int = 0, name: str = "default") -> None:
        self.value = value
        self._name = name

    @classmethod
    def compute_value(cls, name: str, ts: float) -> int:
        logging.getLogger().info(
            "Example compute_value called with name=%s time=%f", name, ts
        )
        return sum(range(1_00_000))

    def _compute_value(self) -> int:
        # we block the thread here to ensure contention
        time.sleep(0.05)
        return self.compute_value(self._name, time.time())

    @functools.cached_property
    def value_functools_cached_property(self) -> int:
        return self._compute_value() + self.value

    @property
    @functools.cache  # noqa: B019
    def value_functools_cache(self) -> int:
        return self._compute_value() + self.value

    @atomic_cached_property
    def value_atomic_cached_property(self) -> int:
        return self._compute_value() + self.value


@pytest.fixture(autouse=True)
def capture_logging(caplog: LogCaptureFixture) -> Generator[None]:
    with caplog.at_level(logging.DEBUG):
        yield


def test_threading_property_types() -> None:
    assert isinstance(Example.value_atomic_cached_property, AtomicCachedProperty)
    assert isinstance(
        Example.value_functools_cached_property, functools.cached_property
    )
    assert isinstance(Example.value_functools_cache, property)


def test_threading_single_thread_safe() -> None:
    instance = Example()
    assert (
        instance.value_functools_cached_property
        == instance.value_atomic_cached_property
        == EXPECTED_VALUE
    )


def run_in_threads(instance: Example, property_name: str) -> None:
    results = []

    def access_property() -> None:
        results.append(instance.__getattribute__(property_name))

    executor = ThreadPoolExecutor(max_workers=WORKER_COUNT)
    futures = [executor.submit(access_property) for _ in range(WORKER_COUNT)]

    wait(futures)
    assert len(results) == WORKER_COUNT
    assert all(result == (EXPECTED_VALUE + instance.value) for result in results)


@pytest.mark.parametrize(
    ["property_name", "expected_call_count"],
    [
        ("value_atomic_cached_property", 1),
        # prior to Python 3.12, cached_property did have a thread lock
        ("value_functools_cached_property", WORKER_COUNT if IS_PY_312 else 1),
        ("value_functools_cache", WORKER_COUNT),
    ],
)
def test_threading_property_caching(
    property_name: str,
    expected_call_count: int,
    mocker: MockerFixture,
    caplog: LogCaptureFixture,
) -> None:
    compute_value_spy = mocker.spy(Example, "compute_value")
    run_in_threads(Example(), property_name)
    assert compute_value_spy.call_count == len(caplog.messages) == expected_call_count


@pytest.mark.parametrize(
    ["property_name", "expected_call_count"],
    [
        ("value_atomic_cached_property", 2),
        # prior to Python 3.12, cached_property did have a thread lock
        ("value_functools_cached_property", (WORKER_COUNT if IS_PY_312 else 1) * 2),
        ("value_functools_cache", WORKER_COUNT * 2),
    ],
)
def test_threading_atomic_cached_property_different_instances(
    property_name: str,
    expected_call_count: int,
    mocker: MockerFixture,
    caplog: LogCaptureFixture,
) -> None:
    compute_value_spy = mocker.spy(Example, "compute_value")

    instance1 = Example(10, "one")
    instance2 = Example(20, "two")

    run_in_threads(instance1, property_name)
    run_in_threads(instance2, property_name)

    assert compute_value_spy.call_count == len(caplog.messages) == expected_call_count

    assert instance1.__getattribute__(property_name) == EXPECTED_VALUE + 10
    assert instance2.__getattribute__(property_name) == EXPECTED_VALUE + 20
