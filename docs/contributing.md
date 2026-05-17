---
title: "Contributing to Poetry"
draft: false
type: docs
layout: single

menu:
  docs:
    weight: 100

note: "Are you viewing this document on GitHub? For the best experience, view it on the website https://python-poetry.org/docs/contributing."
---

# Contributing to Poetry

First off, thanks for taking the time to contribute!

The following is a set of guidelines for contributing to Poetry on GitHub. These are mostly guidelines, not rules. Use
your best judgement, and feel free to propose changes to this document in a pull request.

## How to contribute

### Reporting bugs

This section guides you through submitting a bug report for Poetry.
Following these guidelines helps maintainers and the community understands your report, reproduces the behavior, and finds
related reports.

#### Before submitting a bug report

* **Check the [FAQ](faq.md)** for a list of common questions and problems.
* **Check the [blog](https://python-poetry.org/blog/)** for release notes from recent releases, including steps for upgrading and known issues.
* **Check that your issue does not already exist** in the [issue tracker]( https://github.com/python-poetry/poetry/issues).
* **Make sure your issue is really a bug, and is not a support request or question** better suited for [Discussions](https://github.com/python-poetry/poetry/discussions)
or [Discord](https://discord.com/invite/awxPgve).
* **Try running your commands with the** `--no-cache` **flag**.
* **Try clearing your cache with** `poetry cache clear --all PyPI` **and rerunning your commands**.

*Note:
<ins>If you find a **Closed** issue that seems like it is the same thing that you're experiencing, open a new issue and
include a link to the original issue in the body of your new one.</ins>*

#### How do I submit a bug report?

Bugs concerning Poetry and poetry-core should be submitted to the main [issue tracker](https://github.com/python-poetry/poetry/issues), using the correct
[issue template](https://github.com/python-poetry/poetry/issues/new/choose).

Explain the problem and make it easy for others to search for and understand:

* **Use a clear and descriptive title** for the issue to identify the problem.
* **Describe the exact steps which reproduce the problem** in as many details as possible.
* **Describe the behavior you observed after following the steps** and point out how this is a bug.
* **Explain which behavior you expected to see instead and why.**
* **If the problem involves an unexpected error being raised**, execute the problematic command in **debug** mode
(with `-vvv` flag).

Provide detailed steps for reproduction of your issue:

* **Provide your pyproject.toml file** in a [Gist](https://gist.github.com), pastebin, or example repository after
removing potential private information like private package repositories or names.
* **Provide specific examples to demonstrate the steps to reproduce the issue**. This could be an example repository, a
sequence of steps run in a container, or just a pyproject.toml for very simple cases.
* **Are you unable to reliably reproduce the issue?** If so, provide details about how often the problem happens
and under which conditions it normally happens.

Provide more context by answering these questions:

* **Did the problem start happening recently** (e.g., after updating to a new version of Poetry) or was this always a
problem?
* If the problem started happening recently, **can you reproduce the problem in an older version of Poetry?** What's the
most recent version in which the problem does not happen?
* **Is there anything exotic or unusual about your environment?** This could include use of special container images,
newer CPU architectures like Apple Silicon, or corporate proxies that intercept or modify your network traffic.

Include details about your configuration and environment:

* **Which version of Poetry are you using?** You can get the exact version by running `poetry --version`.
* **What version of Python is being used to run Poetry?** Execute the `poetry debug info` to get this information.
* **What's the name and version of the OS you're using?** Examples include Ubuntu 22.04 or macOS 12.6.

To give others the best chance to understand and reproduce your issue, please be sure to put extra effort into your
reproduction steps. You can both rule out local configuration issues on your end, and ensure others can cleanly
reproduce your issue if attempt all reproductions in a pristine container (or VM), and provide the steps you performed
inside that container/VM in your issue report.

### Suggesting enhancements

This section guides you through submitting an enhancement suggestion for Poetry, including completely new features as
well as improvements to existing functionality. Following these guidelines helps maintainers and the community
understand your suggestion and find related suggestions.

#### Before submitting a suggested enhancement

* **Check the [FAQ](faq.md)** for a list of common questions and problems.
* **Check that your issue does not already exist** in the [issue tracker](https://github.com/python-poetry/poetry/issues).

#### How do I submit a suggested enhancement?

Suggested enhancements concerning Poetry and poetry-core should be submitted to the main [issue tracker](https://github.com/python-poetry/poetry/issues), using the
correct [issue template](https://github.com/python-poetry/poetry/issues/new/choose).

* **Use a clear and descriptive title** for the issue to identify the suggestion.
* **Provide a detailed description of the proposed enhancement**, with specific steps or examples when possible.
* **Describe the current behavior** and **explain which behavior you would like to see instead**, and why.

### Documentation contributions

One of the simplest ways to get started contributing to a project is through improving documentation. Poetry is
constantly evolving, and this means that sometimes our documentation has gaps. You can help by adding missing sections,
editing the existing content to be more accessible, or creating new content such as tutorials, FAQs, etc.

*Note:
GitHub [Discussions](https://github.com/python-poetry/poetry/discussions) and the
[kind/question label](https://github.com/python-poetry/poetry/labels/kind/question) are excellent sources for FAQ
candidates.
*

Issues pertaining to the documentation are usually marked with the [area/docs label](https://github.com/python-poetry/poetry/labels/area/docs), which will also trigger a preview
of the changes as rendered by this website.

### Code contributions

#### Picking an issue

*Note:
<ins>If you are a first time contributor, and are looking for an issue to take on, you might want to look for
at the [contributing page](https://github.com/python-poetry/poetry/contribute) for candidates. We do our best to curate
good issues for first-time contributors there, but do fall behind -- so if you don't see anything good, feel free to
ask.</ins>*

If you would like to take on an issue, feel free to comment on the issue tagging `@python-poetry/triage`.
We are more than happy to discuss solutions on the issue. If you would like help with navigating the code base, are
looking for something to work on, or want feedback on a design or change, join us on our [Discord server](https://discord.com/invite/awxPgve) or
start a [Discussion](https://github.com/python-poetry/poetry/discussions).

#### Local development

Poetry is developed using Poetry. Refer to the [documentation](_index.md) to install Poetry in your local environment.

*Note:
<ins>Poetry's development toolchain requires Python 3.9 or newer.</ins>*

You should first fork the Poetry repository and then clone it locally, so that you can make pull requests against the
project. If you are new to Git and pull request-based development, GitHub provides a
[guide](https://docs.github.com/en/get-started/quickstart/contributing-to-projects) you will find helpful.

Next, you should install Poetry's dependencies, and run the test suite to make sure everything is working as expected:

```bash
poetry install
poetry run pytest
```

If you want to see the coverage stats after the tests are complete, use:

```bash
poetry run pytest --cov=src/poetry --cov-report term
```


When you contribute to Poetry, automated tools will be run to make sure your code is suitable to be merged. Besides
pytest, you will need to make sure your code typechecks properly using [mypy](http://mypy-lang.org/):

```bash
poetry run mypy
```

Finally, a great deal of linting tools are run on your code, to try and ensure consistent code style and root out common
mistakes. The [pre-commit](https://pre-commit.com/) tool is used to install and run these tools, and requires one-time
setup:

```bash
poetry run pre-commit install
```

pre-commit will now run and check your code every time you make a commit. By default, it will only run on changed files,
but you can run it on all files manually (this may be useful if you altered the pre-commit config):

```bash
poetry run pre-commit run --all-files
```

#### Pull requests

* Fill out the pull request body completely and describe your changes as accurately as possible. The pull request body
should be kept up to date as it will usually form the base for the final merge commit and the changelog entry.
* Be sure that your pull request contains tests that cover the changed or added code. Tests are generally required for
code be to be considered mergeable, and code without passing tests will not be merged.
* Ensure your pull request passes the mypy and pre-commit checks. Remember that you can run these tools locally
instead of relying on remote CI.
* If your changes warrant a documentation change, the pull request must also update the documentation. Make sure to
review the documentation preview generated by CI for any rendering issues.


*Note:
<ins>Make sure your branch is [rebased](https://docs.github.com/en/get-started/using-git/about-git-rebase) against the latest
base branch. A maintainer might ask you to ensure the branch is up-to-date prior to merging your pull request
(especially if there have been CI changes on the base branch), and will also ask you to fix any conflicts.</ins>*

All pull requests, unless otherwise instructed, need to be first accepted into the `main` branch. Maintainers will
generally decide if any backports to other branches are required, and carry them out as needed.

### Issue triage

*Note:
<ins>If you have an issue that hasn't had any attention, you can ping us `@python-poetry/triage` on the issue. Please give us
reasonable time to get to your issue first, and avoid pinging any individuals directly, especially if they are not part
of the Poetry team.</ins>*

If you are helping with the triage of reported issues, this section provides some useful information to assist you in
your contribution.

#### Triage steps

1. Determine what area and versions of Poetry the issue is related to, and set the appropriate labels (e.g.
`version/x.x.x`, `area/docs`, `area/venv`), and remove the `status/triage` label.
2. If requested information (such as debug logs, pyproject.toml, etc.) is not provided and is relevant, request it from
the author.
   1. Set the `status/waiting-on-response` label while waiting to hear back from the author.
3. Attempt to reproduce the issue with the reported Poetry version or request further clarification from the author.
4. Ensure the issue is not already resolved. Try reproducing it on the latest stable release, the latest prerelease (if
present), and the development branch.
5. If the issue cannot be reproduced,
   1. request more reproduction steps and clarification from the issue's author,
   2. set the `status/needs-reproduction` label,
   3. close the issue if there is no reproduction forthcoming.
6. If the issue can be reproduced,
   1. comment on the issue confirming so,
   2. set the `status/confirmed` label,
   3. if possible, identify the root cause of the issue,
   4. if interested, attempt to fix it via a pull request.

#### Multiple versions

When trying to reproduce issues, you often want to use multiple versions of Poetry at the same time.
[pipx](https://pypa.github.io/pipx/) makes this easy to do:

```sh
pipx install --suffix @1.2.1 'poetry==1.2.1'
pipx install --suffix @1.3.0rc1 'poetry==1.3.0rc1'
pipx install --suffix @main 'poetry @ git+https://github.com/python-poetry/poetry'
pipx install --suffix @local '/path/to/local/clone/of/poetry'

# now you can use any of the chosen versions of Poetry with their configured suffix, e.g.
poetry@main --version
```

*Note:
<ins> Do not forget to `pipx upgrade poetry@main` before using it, to make sure you have the latest changes.</ins>*


```sh
pipx install --suffix @pr1234 git+https://github.com/python-poetry/poetry.git@refs/pull/1234/head
```
*Note:
<ins>This mechanism can also be used to test pull requests by using GitHub's pull request remote refs:</ins>*
