"""Tests for the --use-tool-poetry flag in poetry init command."""

from __future__ import annotations

from typing import Any
from typing import cast

from poetry.console.commands.init import InitCommand
from poetry.layouts import layout


def test_init_command_has_use_tool_poetry_option() -> None:
    """Test that the InitCommand has the --use-tool-poetry option."""
    command = InitCommand()
    options = [opt.name for opt in command.options]
    assert "use-tool-poetry" in options


def test_layout_supports_use_tool_poetry_parameter() -> None:
    """Test that Layout class accepts use_tool_poetry parameter."""
    layout_instance = layout("standard")(
        "test-package",
        "0.1.0",
        description="Test package",
        author="Test Author <test@example.com>",
        python=">=3.8",
        use_tool_poetry=True,
    )
    assert hasattr(layout_instance, "_use_tool_poetry")
    assert layout_instance._use_tool_poetry is True


def test_generate_project_content_with_tool_poetry_format() -> None:
    """Test that generate_project_content creates tool.poetry format when flag is True."""
    layout_instance = layout("standard")(
        "test-package",
        "0.1.0",
        description="Test package",
        author="Test Author <test@example.com>",
        python=">=3.8",
        dependencies={"requests": "^2.25.0"},
        use_tool_poetry=True,
    )

    content = layout_instance.generate_project_content()

    tool = cast("dict[str, Any]", content.get("tool", {}))
    poetry_section = cast("dict[str, Any]", tool.get("poetry", {}))

    # Should have tool.poetry section with name
    assert "tool" in content
    assert "poetry" in tool
    assert poetry_section["name"] == "test-package"

    # Should NOT have project section
    assert "project" not in content

    # Should have dependencies in tool.poetry.dependencies
    assert "dependencies" in poetry_section
    assert "requests" in poetry_section["dependencies"]


def test_generate_project_content_with_project_format() -> None:
    """Test that generate_project_content creates project format when flag is False."""
    layout_instance = layout("standard")(
        "test-package",
        "0.1.0",
        description="Test package",
        author="Test Author <test@example.com>",
        python=">=3.8",
        dependencies={"requests": "^2.25.0"},
        use_tool_poetry=False,
    )

    content = layout_instance.generate_project_content()

    project_section = cast("dict[str, Any]", content.get("project", {}))

    # Should have project section
    assert "project" in content
    assert project_section["name"] == "test-package"

    # Should have dependencies in project.dependencies
    assert "dependencies" in project_section
    assert len(project_section["dependencies"]) > 0


def test_author_format_difference() -> None:
    """Test that author format differs between the two formats."""
    # Tool poetry format
    layout_tool = layout("standard")(
        "test-package",
        "0.1.0",
        author="Test Author <test@example.com>",
        use_tool_poetry=True,
    )
    content_tool = layout_tool.generate_project_content()

    # Project format
    layout_project = layout("standard")(
        "test-package",
        "0.1.0",
        author="Test Author <test@example.com>",
        use_tool_poetry=False,
    )
    content_project = layout_project.generate_project_content()

    tool = cast("dict[str, Any]", content_tool.get("tool", {}))
    poetry_section = cast("dict[str, Any]", tool.get("poetry", {}))
    project_section = cast("dict[str, Any]", content_project.get("project", {}))

    # Tool poetry format: simple string
    assert poetry_section["authors"][0] == "Test Author <test@example.com>"

    # Project format: structured object
    assert project_section["authors"][0]["name"] == "Test Author"
    assert project_section["authors"][0]["email"] == "test@example.com"
