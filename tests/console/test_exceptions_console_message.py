from __future__ import annotations

import pytest

from poetry.console.exceptions import ConsoleMessage


@pytest.mark.parametrize(
    ("text", "expected_stripped"),
    [
        ("<info>Hello, World!</info>", "Hello, World!"),
        ("<b>Bold</b>", "Bold"),
        ("<i>Italic</i>", "Italic"),
    ],
)
def test_stripped_property(text: str, expected_stripped: str) -> None:
    """Test the stripped property with various tagged inputs."""
    message = ConsoleMessage(text)
    assert message.stripped == expected_stripped


@pytest.mark.parametrize(
    ("text", "tag", "expected"),
    [
        ("Hello, World!", "info", "<info>Hello, World!</>"),
        ("Error occurred", "error", "<error>Error occurred</>"),
        ("", "info", ""),  # Test with empty input
    ],
)
def test_wrap(text: str, tag: str, expected: str) -> None:
    """Test the wrap method with various inputs."""
    message = ConsoleMessage(text)
    assert message.wrap(tag).text == expected


@pytest.mark.parametrize(
    ("text", "indent", "expected"),
    [
        ("Hello, World!", "    ", "    Hello, World!"),
        ("Line 1\nLine 2", ">>", ">>Line 1\n>>Line 2"),
        ("", "  ", ""),  # Test with empty input
        (" ", "  ", "  "),  # Test with whitespace input
    ],
)
def test_indent(text: str, indent: str, expected: str) -> None:
    """Test the indent method with various inputs."""
    message = ConsoleMessage(text)
    assert message.indent(indent).text == expected


@pytest.mark.parametrize(
    ("text", "title", "indent", "expected"),
    [
        ("Hello, World!", "Greeting", "", "<b>Greeting:</>\nHello, World!"),
        (
            "This is a message.",
            "Section Title",
            "  ",
            "<b>Section Title:</>\n  This is a message.",
        ),
        ("", "Title", "", ""),  # Test with empty text
        ("Multi-line\nText", "Title", ">>>", "<b>Title:</>\n>>>Multi-line\n>>>Text"),
    ],
)
def test_make_section(text: str, title: str, indent: str, expected: str) -> None:
    """Test the make_section method with various inputs."""
    message = ConsoleMessage(text)
    assert message.make_section(title, indent).text == expected
