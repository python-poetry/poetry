import re

MODIFIERS = (
    "[._-]?"
    "((?!post)(?:beta|b|c|pre|RC|alpha|a|patch|pl|p|dev)(?:(?:[.-]?\d+)*)?)?"
    "([+-]?([0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?"
)

_COMPLETE_VERSION = "v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?{}(?:\+[^\s]+)?".format(
    MODIFIERS
)

COMPLETE_VERSION = re.compile("(?i)" + _COMPLETE_VERSION)

CARET_CONSTRAINT = re.compile("(?i)^\^({})$".format(_COMPLETE_VERSION))
TILDE_CONSTRAINT = re.compile("(?i)^~(?!=)({})$".format(_COMPLETE_VERSION))
TILDE_PEP440_CONSTRAINT = re.compile("(?i)^~=({})$".format(_COMPLETE_VERSION))
X_CONSTRAINT = re.compile("^(!=|==)?\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.[xX*])+$")
BASIC_CONSTRAINT = re.compile(
    "(?i)^(<>|!=|>=?|<=?|==?)?\s*({}|dev)".format(_COMPLETE_VERSION)
)
