# OSS report: python-poetry/poetry#10449

**Status:** DONE

**FLAG: SMALL FIX** - UX improvement to an error path, a few lines in one command.

## Issue check
Open, no assignee, no linked PRs, and no claim comments when checked (2026-10-27).

## Root cause
1. `poetry add pkg@latest` writes the dependency to the target group (main by default). The same package is already declared in another group (e.g. `dev`) with an older constraint.
2. The solver finds the two constraints non-overlapping and raises `IncompatibleConstraintsError`.
3. `AddCommand` doesn't handle it, so the user gets a raw traceback with no hint that another group needs updating.

## Diff summary
- `src/poetry/console/commands/add.py`: catch `IncompatibleConstraintsError` around `installer.run()`. Print the error, list the other groups that declare the package, suggest `poetry add --group <g> <pkg>@latest`, print "No changes were applied.", and return 1. `pyproject.toml` is not written.
- `tests/console/commands/test_add.py`: new `test_add_latest_to_main_when_present_in_other_group`. Before the fix it fails with the uncaught exception.

## Tests
```
.venv/bin/python -m pytest tests/console/commands/test_add.py -q
85 passed in 2.67s
uvx ruff check <changed files>   -> All checks passed!
uvx ruff format <changed files>  -> 2 files left unchanged
```
mypy was not run (not installed in the env).

## Risks
- The hint only fires for `IncompatibleConstraintsError`. Other solver errors are unchanged.
- It suggests only the first conflicting group. This is deliberately minimal.
- Maintainers might prefer a different fix, such as updating the group's constraint automatically. This one only improves the message.

## Draft PR description
**Title:** Improve error when `poetry add` conflicts with a dependency in another group

Resolves: #10449

When a package is already declared in another dependency group with a conflicting constraint (e.g. `poetry add pytest@latest` while `pytest` is pinned in `dev`), the solver raised an uncaught `IncompatibleConstraintsError` and the user saw a traceback.

`add` now catches it, reports the conflict, names the other group(s) declaring the package, and suggests `poetry add --group <group> <package>@latest`. No changes are applied.

Added a test for the case.

## Estimated cost
About $1.
