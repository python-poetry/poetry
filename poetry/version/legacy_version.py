import re

from .base import BaseVersion


class LegacyVersion(BaseVersion):
    def __init__(self, version):
        self._version = str(version)
        self._key = _legacy_cmpkey(self._version)

    def __str__(self):
        return self._version

    def __repr__(self):
        return "<LegacyVersion({0})>".format(repr(str(self)))

    @property
    def public(self):
        return self._version

    @property
    def base_version(self):
        return self._version

    @property
    def local(self):
        return None

    @property
    def is_prerelease(self):
        return False

    @property
    def is_postrelease(self):
        return False


_legacy_version_component_re = re.compile(r"(\d+ | [a-z]+ | \.| -)", re.VERBOSE)

_legacy_version_replacement_map = {
    "pre": "c",
    "preview": "c",
    "-": "final-",
    "rc": "c",
    "dev": "@",
}


def _parse_version_parts(s):
    for part in _legacy_version_component_re.split(s):
        part = _legacy_version_replacement_map.get(part, part)

        if not part or part == ".":
            continue

        if part[:1] in "0123456789":
            # pad for numeric comparison
            yield part.zfill(8)
        else:
            yield "*" + part

    # ensure that alpha/beta/candidate are before final
    yield "*final"


def _legacy_cmpkey(version):
    # We hardcode an epoch of -1 here. A PEP 440 version can only have a epoch
    # greater than or equal to 0. This will effectively put the LegacyVersion,
    # which uses the defacto standard originally implemented by setuptools,
    # as before all PEP 440 versions.
    epoch = -1

    # This scheme is taken from pkg_resources.parse_version setuptools prior to
    # it's adoption of the packaging library.
    parts = []
    for part in _parse_version_parts(version.lower()):
        if part.startswith("*"):
            # remove "-" before a prerelease tag
            if part < "*final":
                while parts and parts[-1] == "*final-":
                    parts.pop()

            # remove trailing zeros from each series of numeric parts
            while parts and parts[-1] == "00000000":
                parts.pop()

        parts.append(part)
    parts = tuple(parts)

    return epoch, parts
