# -*- coding: utf-8 -*-


class Operation:

    def __init__(self, reason: str = None) -> None:
        self._reason = reason

    @property
    def job_type(self):
        raise NotImplementedError

    @property
    def reason(self) -> str:
        return self._reason

    def format_version(self, package):
        return package.full_pretty_version
