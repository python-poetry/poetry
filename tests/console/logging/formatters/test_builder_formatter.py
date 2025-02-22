from __future__ import annotations

import pytest

from poetry.console.logging.formatters.builder_formatter import BuilderLogFormatter


@pytest.mark.parametrize(
    "input_msg, expected_output",
    [
        ("Building package", "  - Building <info>package</info>"),
        ("Built package", "  - Built <success>package</success>"),
        ("Adding: dependency", "  - Adding: <b>dependency</b>"),
        (
            "Executing build script: setup.py",
            "  - Executing build script: <b>setup.py</b>",
        ),
        ("Some other message", "Some other message"),  # No formatting should be applied
        ("", ""),  # Edge case: Empty string
        (
            "  Building package  ",
            "  Building package  ",
        ),  # Edge case: Whitespace handling
        ("building package", "building package"),  # Edge case: Case sensitivity
    ],
)
def test_builder_log_formatter(input_msg, expected_output):
    formatter = BuilderLogFormatter()
    assert formatter.format(input_msg) == expected_output
