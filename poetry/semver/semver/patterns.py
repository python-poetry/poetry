import re

MODIFIERS = (
    '[._-]?'
    '((?:beta|b|c|pre|RC|alpha|a|patch|pl|p|dev)(?:(?:[.-]?\d+)*)?)?'
    '((?:[+-]|post)?([0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?'
)

_COMPLETE_VERSION = 'v?(\d+)(?:\.(\d+))?(?:\.(\d+))?{}(?:\+[^\s]+)?'.format(MODIFIERS)

COMPLETE_VERSION = re.compile('(?i)' + _COMPLETE_VERSION)

CARET_CONSTRAINT = re.compile('(?i)^\^({})$'.format(_COMPLETE_VERSION))
TILDE_CONSTRAINT = re.compile('(?i)^~=?({})$'.format(_COMPLETE_VERSION))
X_CONSTRAINT = re.compile('^(!= ?|==)?v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.[xX*])+$')
BASIC_CONSTRAINT = re.compile('(?i)^(<>|!=|>=?|<=?|==?)?\s*({})'.format(_COMPLETE_VERSION))
