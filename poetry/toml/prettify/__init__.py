from ._version import VERSION

__version__ = VERSION


def prettify(toml_text):
    """
    Prettifies and returns the TOML file content provided.
    """
    from .parser import parse_tokens
    from .lexer import tokenize
    from .prettifier import prettify as element_prettify

    tokens = tokenize(toml_text, is_top_level=True)
    elements = parse_tokens(tokens)
    prettified = element_prettify(elements)
    return ''.join(pretty_element.serialized() for pretty_element in prettified)


def prettify_from_file(file_path):
    """
    Reads, prettifies and returns the TOML file specified by the file_path.
    """
    with open(file_path, 'r') as fp:
        return prettify(fp.read())
