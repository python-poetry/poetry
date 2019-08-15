import re

MODIFIERS = (
    "[._-]?"
    r"((?!post)(?:beta|b|c|pre|RC|alpha|a|patch|pl|p|dev)(?:(?:[.-]?\d+)*)?)?"
    r"([+-]?([0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?"
)

_COMPLETE_VERSION = r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?{}(?:\+[^\s]+)?".format(
    MODIFIERS
)

COMPLETE_VERSION = re.compile("(?i)" + _COMPLETE_VERSION)

CARET_CONSTRAINT = re.compile(r"(?i)^\^({})$".format(_COMPLETE_VERSION))
TILDE_CONSTRAINT = re.compile("(?i)^~(?!=)({})$".format(_COMPLETE_VERSION))
TILDE_PEP440_CONSTRAINT = re.compile("(?i)^~=({})$".format(_COMPLETE_VERSION))
X_CONSTRAINT = re.compile(r"^(!=|==)?\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.[xX*])+$")
BASIC_CONSTRAINT = re.compile(
    r"(?i)^(<>|!=|>=?|<=?|==?)?\s*({}|dev)".format(_COMPLETE_VERSION)
)
