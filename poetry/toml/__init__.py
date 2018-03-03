"""
This toml module is a port with changes and fixes
of [contoml](https://github.com/jumpscale7/python-consistent-toml).
"""


from .toml_file import TOMLFile
from .prettify.lexer import tokenize as lexer
from .prettify.parser import parse_tokens


def loads(text):
    """
    Parses TOML text into a dict-like object and returns it.
    """
    tokens = tuple(lexer(text, is_top_level=True))
    elements = parse_tokens(tokens)

    return TOMLFile(elements)


def load(file_path):
    """
    Parses a TOML file into a dict-like object and returns it.
    """
    with open(file_path) as fd:
        return loads(fd.read())


def dumps(value):
    """
    Dumps a data structure to TOML source code.

    The given value must be either a dict of dict values, a dict,
    or a TOML file constructed by this module.
    """
    if not isinstance(value, TOMLFile):
        raise RuntimeError(
            'Can only dump a TOMLFile instance loaded by load() or loads()'
        )

    return value.dumps()


def dump(obj, file_path, prettify=False):
    """
    Dumps a data structure to the filesystem as TOML.

    The given value must be either a dict of dict values, a dict,
    or a TOML file constructed by this module.
    """
    with open(file_path, 'w') as fp:
        fp.write(dumps(obj))
