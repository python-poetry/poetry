from __future__ import annotations

from subprocess import CalledProcessError

import pytest

from poetry.console.exceptions import ConsoleMessage
from poetry.console.exceptions import PoetryRuntimeError


@pytest.mark.parametrize(
    ("reason", "messages", "exit_code", "expected_reason"),
    [
        ("Error occurred!", None, 1, "Error occurred!"),  # Default scenario
        (
            "Specific error",
            [ConsoleMessage("Additional details.")],
            2,
            "Specific error",
        ),  # Custom exit code and messages
        ("Minimal error", [], 0, "Minimal error"),  # No additional messages
    ],
)
def test_poetry_runtime_error_init(
    reason: str,
    messages: list[ConsoleMessage] | None,
    exit_code: int,
    expected_reason: str,
) -> None:
    """Test the basic initialization of the PoetryRuntimeError class."""
    error = PoetryRuntimeError(reason, messages, exit_code)
    assert error.exit_code == exit_code
    assert str(error) == expected_reason
    assert isinstance(error._messages[0], ConsoleMessage)
    assert error._messages[0].text == reason


@pytest.mark.parametrize(
    ("debug", "strip", "indent", "messages", "expected_text"),
    [
        (
            False,
            False,
            "",
            [
                ConsoleMessage("Basic message"),
                ConsoleMessage("Debug message", debug=True),
            ],
            "Error\n\nBasic message\n\nYou can also run your <c1>poetry</> command with <c1>-v</> to see more information.",
        ),  # Debug message ignored
        (
            True,
            False,
            "",
            [
                ConsoleMessage("Info message"),
                ConsoleMessage("Debug message", debug=True),
            ],
            "Error\n\nInfo message\n\nDebug message",
        ),  # Debug message included in verbose mode
        (
            True,
            True,
            "",
            [
                ConsoleMessage("<b>Bolded message</b>"),
                ConsoleMessage("<i>Debug Italics Message</i>", debug=True),
            ],
            "Error\n\nBolded message\n\nDebug Italics Message",
        ),  # Stripped tags and debug message
        (
            False,
            False,
            "    ",
            [ConsoleMessage("Error occurred!")],
            "    Error\n    \n    Error occurred!",
        ),  # Indented message
    ],
)
def test_poetry_runtime_error_get_text(
    debug: bool,
    strip: bool,
    indent: str,
    messages: list[ConsoleMessage],
    expected_text: str,
) -> None:
    """Test the get_text method of PoetryRuntimeError."""
    error = PoetryRuntimeError("Error", messages)
    text = error.get_text(debug=debug, strip=strip, indent=indent)
    assert text == expected_text


@pytest.mark.parametrize(
    ("reason", "exception", "info", "expected_message_texts"),
    [
        (
            "Command failed",
            None,
            None,
            ["Command failed", ""],  # No exception or additional info
        ),
        (
            "Command failure",
            Exception("An exception occurred"),
            None,
            [
                "Command failure",
                "<b>Exception:</>\n    | An exception occurred",
                "",
            ],  # Exception message included
        ),
        (
            "Subprocess error",
            CalledProcessError(1, ["cmd"], b"stdout", b"stderr"),
            ["Additional info"],
            [
                "Subprocess error",
                "<warning><b>Exception:</>\n"
                "    | Command '['cmd']' returned non-zero exit status 1.</>",
                "<warning><b>Output:</>\n" "    | stdout</>",
                "<warning><b>Errors:</>\n" "    | stderr</>",
                "<info>Additional info</>",
                "You can test the failed command by executing:\n\n    <c1>cmd</c1>",
            ],
        ),
    ],
)
def test_poetry_runtime_error_create(
    reason: str,
    exception: Exception,
    info: list[str],
    expected_message_texts: list[str],
) -> None:
    """Test the create class method of PoetryRuntimeError."""
    error = PoetryRuntimeError.create(reason, exception, info)

    assert isinstance(error, PoetryRuntimeError)
    assert all(isinstance(msg, ConsoleMessage) for msg in error._messages)

    actual_texts = [msg.text for msg in error._messages]
    assert actual_texts == expected_message_texts
