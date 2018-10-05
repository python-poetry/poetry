# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
from __future__ import absolute_import, division, print_function

import string
import re

try:
    import urllib.parse as urlparse
except ImportError:
    from urlparse import urlparse

from pyparsing import stringStart, stringEnd, originalTextFor, ParseException
from pyparsing import ZeroOrMore, Word, Optional, Regex, Combine
from pyparsing import Literal as L  # noqa

from poetry.semver import parse_constraint

from .markers import MARKER_EXPR
from .markers import parse_marker


LEGACY_REGEX = r"""
    (?P<operator>(==|!=|<=|>=|<|>))
    \s*
    (?P<version>
        [^,;\s)]* # Since this is a "legacy" specifier, and the version
                  # string can be just about anything, we match everything
                  # except for whitespace, a semi-colon for marker support,
                  # a closing paren since versions can be enclosed in
                  # them, and a comma since it's a version separator.
    )
    """


REGEX = r"""
            (?P<operator>(~=|==|!=|<=|>=|<|>|===))
            (?P<version>
                (?:
                    # The identity operators allow for an escape hatch that will
                    # do an exact string match of the version you wish to install.
                    # This will not be parsed by PEP 440 and we cannot determine
                    # any semantic meaning from it. This operator is discouraged
                    # but included entirely as an escape hatch.
                    (?<====)  # Only match for the identity operator
                    \s*
                    [^\s]*    # We just match everything, except for whitespace
                              # since we are only testing for strict identity.
                )
                |
                (?:
                    # The (non)equality operators allow for wild card and local
                    # versions to be specified so we have to define these two
                    # operators separately to enable that.
                    (?<===|!=)            # Only match for equals and not equals

                    \s*
                    v?
                    (?:[0-9]+!)?          # epoch
                    [0-9]+(?:\.[0-9]+)*   # release
                    (?:                   # pre release
                        [-_\.]?
                        (a|b|c|rc|alpha|beta|pre|preview)
                        [-_\.]?
                        [0-9]*
                    )?
                    (?:                   # post release
                        (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                    )?

                    # You cannot use a wild card and a dev or local version
                    # together so group them with a | and make them optional.
                    (?:
                        (?:[-_\.]?dev[-_\.]?[0-9]*)?         # dev release
                        (?:\+[a-z0-9]+(?:[-_\.][a-z0-9]+)*)? # local
                        |
                        \.\*  # Wild card syntax of .*
                    )?
                )
                |
                (?:
                    # The compatible operator requires at least two digits in the
                    # release segment.
                    (?<=~=)               # Only match for the compatible operator

                    \s*
                    v?
                    (?:[0-9]+!)?          # epoch
                    [0-9]+(?:\.[0-9]+)+   # release  (We have a + instead of a *)
                    (?:                   # pre release
                        [-_\.]?
                        (a|b|c|rc|alpha|beta|pre|preview)
                        [-_\.]?
                        [0-9]*
                    )?
                    (?:                                   # post release
                        (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                    )?
                    (?:[-_\.]?dev[-_\.]?[0-9]*)?          # dev release
                )
                |
                (?:
                    # All other operators only allow a sub set of what the
                    # (non)equality operators do. Specifically they do not allow
                    # local versions to be specified nor do they allow the prefix
                    # matching wild cards.
                    (?<!==|!=|~=)         # We have special cases for these
                                          # operators so we want to make sure they
                                          # don't match here.

                    \s*
                    v?
                    (?:[0-9]+!)?          # epoch
                    [0-9]+(?:\.[0-9]+)*   # release
                    (?:                   # pre release
                        [-_\.]?
                        (a|b|c|rc|alpha|beta|pre|preview)
                        [-_\.]?
                        [0-9]*
                    )?
                    (?:                                   # post release
                        (?:-[0-9]+)|(?:[-_\.]?(post|rev|r)[-_\.]?[0-9]*)
                    )?
                    (?:[-_\.]?dev[-_\.]?[0-9]*)?          # dev release
                )
            )
"""


class InvalidRequirement(ValueError):
    """
    An invalid requirement was found, users should refer to PEP 508.
    """


ALPHANUM = Word(string.ascii_letters + string.digits)

LBRACKET = L("[").suppress()
RBRACKET = L("]").suppress()
LPAREN = L("(").suppress()
RPAREN = L(")").suppress()
COMMA = L(",").suppress()
SEMICOLON = L(";").suppress()
AT = L("@").suppress()

PUNCTUATION = Word("-_.")
IDENTIFIER_END = ALPHANUM | (ZeroOrMore(PUNCTUATION) + ALPHANUM)
IDENTIFIER = Combine(ALPHANUM + ZeroOrMore(IDENTIFIER_END))

NAME = IDENTIFIER("name")
EXTRA = IDENTIFIER

URI = Regex(r"[^ ]+")("url")
URL = AT + URI

EXTRAS_LIST = EXTRA + ZeroOrMore(COMMA + EXTRA)
EXTRAS = (LBRACKET + Optional(EXTRAS_LIST) + RBRACKET)("extras")

VERSION_PEP440 = Regex(REGEX, re.VERBOSE | re.IGNORECASE)
VERSION_LEGACY = Regex(LEGACY_REGEX, re.VERBOSE | re.IGNORECASE)

VERSION_ONE = VERSION_PEP440 ^ VERSION_LEGACY
VERSION_MANY = Combine(
    VERSION_ONE + ZeroOrMore(COMMA + VERSION_ONE), joinString=",", adjacent=False
)("_raw_spec")
_VERSION_SPEC = Optional(((LPAREN + VERSION_MANY + RPAREN) | VERSION_MANY))
_VERSION_SPEC.setParseAction(lambda s, l, t: t._raw_spec or "")

VERSION_SPEC = originalTextFor(_VERSION_SPEC)("specifier")
VERSION_SPEC.setParseAction(lambda s, l, t: t[1])

MARKER_EXPR = originalTextFor(MARKER_EXPR())("marker")
MARKER_EXPR.setParseAction(
    lambda s, l, t: parse_marker(s[t._original_start : t._original_end])
)
MARKER_SEPERATOR = SEMICOLON
MARKER = MARKER_SEPERATOR + MARKER_EXPR

VERSION_AND_MARKER = VERSION_SPEC + Optional(MARKER)
URL_AND_MARKER = URL + Optional(MARKER)

NAMED_REQUIREMENT = NAME + Optional(EXTRAS) + (URL_AND_MARKER | VERSION_AND_MARKER)

REQUIREMENT = stringStart + NAMED_REQUIREMENT + stringEnd


class Requirement(object):
    """Parse a requirement.

    Parse a given requirement string into its parts, such as name, specifier,
    URL, and extras. Raises InvalidRequirement on a badly-formed requirement
    string.
    """

    def __init__(self, requirement_string):
        try:
            req = REQUIREMENT.parseString(requirement_string)
        except ParseException as e:
            raise InvalidRequirement(
                'Invalid requirement, parse error at "{0!r}"'.format(
                    requirement_string[e.loc : e.loc + 8]
                )
            )

        self.name = req.name
        if req.url:
            parsed_url = urlparse.urlparse(req.url)
            if not (parsed_url.scheme and parsed_url.netloc) or (
                not parsed_url.scheme and not parsed_url.netloc
            ):
                raise InvalidRequirement("Invalid URL given")
            self.url = req.url
        else:
            self.url = None

        self.extras = set(req.extras.asList() if req.extras else [])
        constraint = req.specifier
        if not constraint:
            constraint = "*"

        self.constraint = parse_constraint(constraint)
        self.pretty_constraint = constraint

        self.marker = req.marker if req.marker else None

    def __str__(self):
        parts = [self.name]

        if self.extras:
            parts.append("[{0}]".format(",".join(sorted(self.extras))))

        if self.pretty_constraint:
            parts.append(self.pretty_constraint)

        if self.url:
            parts.append("@ {0}".format(self.url))

        if self.marker:
            parts.append("; {0}".format(self.marker))

        return "".join(parts)

    def __repr__(self):
        return "<Requirement({0!r})>".format(str(self))
