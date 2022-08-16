# -*- coding: utf-8 -*-

from typing import Union


class Operation(object):
    def __init__(
        self, reason=None, priority=0
    ):  # type: (Union[str, None], int) -> None
        self._reason = reason

        self._skipped = False
        self._skip_reason = None
        self._priority = priority

    @property
    def job_type(self):  # type: () -> str
        raise NotImplementedError

    @property
    def reason(self):  # type: () -> str
        return self._reason

    @property
    def skipped(self):  # type: () -> bool
        return self._skipped

    @property
    def skip_reason(self):  # type: () -> Union[str, None]
        return self._skip_reason

    @property
    def priority(self):  # type: () -> int
        return self._priority

    @property
    def package(self):
        raise NotImplementedError()

    def format_version(self, package):  # type: (...) -> str
        return package.full_pretty_version

    def skip(self, reason):  # type: (str) -> Operation
        self._skipped = True
        self._skip_reason = reason

        return self

    def unskip(self):  # type: () -> Operation
        self._skipped = False
        self._skip_reason = None

        return self
