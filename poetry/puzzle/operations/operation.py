# -*- coding: utf-8 -*-


class Operation:

    def __init__(self, reason: str = None) -> None:
        self._reason = reason

        self._skipped = False
        self._skip_reason = None

    @property
    def job_type(self) -> str:
        raise NotImplementedError

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def skipped(self) -> bool:
        return self._skipped

    @property
    def skip_reason(self):
        return self._skip_reason

    def format_version(self, package) -> str:
        return package.full_pretty_version

    def skip(self, reason: str) -> None:
        self._skipped = True
        self._skip_reason = reason
