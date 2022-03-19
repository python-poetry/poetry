---
title: "Contributing to Poetry"
draft: false
type: docs
layout: single

menu:
  docs:
    weight: 100
---

# Contributing to Poetry

First off, thanks for taking the time to contribute!

The following is a set of guidelines for contributing to Poetry on GitHub. These are mostly guidelines, not rules. Use your best judgement, and feel free to propose changes to this document in a pull request.

#### Table of contents

[How to contribute](#how-to-contribute)

  * [Reporting bugs](#reporting-bugs)
  * [Suggesting enhancements](#suggesting-enhancements)
  * [Contributing to documentation](#contributing-to-documentation)
  * [Contributing to code](#contributing-to-code)
  * [Issue triage](#issue-triage)
  * [Git workflow](#git-workflow)


## How to contribute

### Reporting bugs

This section guides you through submitting a bug report for Poetry.
Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.

Before creating bug reports, please check [this list](#before-submitting-a-bug-report) to be sure that you need to create one. When you are creating a bug report, please include as many details as possible. Fill out the [required template](https://github.com/python-poetry/poetry/blob/master/.github/ISSUE_TEMPLATE/---bug-report.md), the information it asks helps the maintainers resolve the issue faster.

> **Note:** If you find a **Closed** issue that seems like it is the same thing that you're experiencing, open a new issue and include a link to the original issue in the body of your new one.

#### Before submitting a bug report

* **Check the [FAQs on the official website](https://python-poetry.org/docs/faq)** for a list of common questions and problems.
* **Check that your issue does not already exist in the [issue tracker](https://github.com/python-poetry/poetry/issues)**.

#### How do I submit a bug report?

Bugs are tracked on the [official issue tracker](https://github.com/python-poetry/poetry/issues) where you can create a new one and provide the following information by filling in [the template](https://github.com/python-poetry/poetry/blob/master/.github/ISSUE_TEMPLATE/---bug-report.md).

Explain the problem and include additional details to help maintainers reproduce the problem:

* **Use a clear and descriptive title** for the issue to identify the problem.
* **Describe the exact steps which reproduce the problem** in as many details as possible.
* **Provide your pyproject.toml file** in a [Gist](https://gist.github.com) after removing potential private information (like private package repositories).
* **Provide specific examples to demonstrate the steps to reproduce the issue**. Include links to files or GitHub projects, or copy-paste-able snippets, which you use in those examples.
* **Describe the behavior you observed after following the steps** and point out what exactly is the problem with that behavior.
* **Explain which behavior you expected to see instead and why.**
* **If the problem is an unexpected error being raised**, execute the corresponding command in **debug** mode (the `-vvv` option).

Provide more context by answering these questions:

* **Did the problem start happening recently** (e.g. after updating to a new version of Poetry) or was this always a problem?
* If the problem started happening recently, **can you reproduce the problem in an older version of Poetry?** What's the most recent version in which the problem doesn't happen?
* **Can you reliably reproduce the issue?** If not, provide details about how often the problem happens and under which conditions it normally happens.

Include details about your configuration and environment:

* **Which version of Poetry are you using?** You can get the exact version by running `poetry -V` in your terminal.
* **Which Python version Poetry has been installed for?** Execute the `debug:info` to get the information.
* **What's the name and version of the OS you're using**?


### Suggesting enhancements

This section guides you through submitting an enhancement suggestion for Poetry, including completely new features and minor improvements to existing functionality. Following these guidelines helps maintainers and the community understand your suggestion and find related suggestions.

Before creating enhancement suggestions, please check [this list](#before-submitting-an-enhancement-suggestion) as you might find out that you don't need to create one. When you are creating an enhancement suggestion, please [include as many details as possible](#how-do-i-submit-an-enhancement-suggestion). Fill in [the template](https://github.com/python-poetry/poetry/blob/master/.github/ISSUE_TEMPLATE/---feature-request.md), including the steps that you imagine you would take if the feature you're requesting existed.

#### Before submitting an enhancement suggestion

* **Check the [FAQs on the official website](https://python-poetry.org/docs/faq)** for a list of common questions and problems.
* **Check that your issue does not already exist in the [issue tracker](https://github.com/python-poetry/poetry/issues)**.

#### How do I submit an Enhancement suggestion?

Enhancement suggestions are tracked on the [official issue tracker](https://github.com/python-poetry/poetry/issues) where you can create a new one and provide the following information:

* **Use a clear and descriptive title** for the issue to identify the suggestion.
* **Provide a step-by-step description of the suggested enhancement** in as many details as possible.
* **Provide specific examples to demonstrate the steps**..
* **Describe the current behavior** and **explain which behavior you expected to see instead** and why.

### Contributing to documentation

One of the simplest ways to get started contributing to a project is through improving documentation. Poetry is constantly evolving, this means that sometimes our documentation has gaps. You can help by
adding missing sections, editing the existing content so it is more accessible or creating new content (tutorials, FAQs, etc).

{{% note %}}
A great way to understand Poetry's design and how it all fits together, is to add FAQ entries for commonly
asked questions. Poetry members usually mark issues with [candidate/faq](https://github.com/python-poetry/poetry/issues?q=is%3Aissue+label%3Acandidate%2Ffaq+) to indicate that the issue either contains a response
that explains how something works or might benefit from an entry in the FAQ.
{{% /note %}}

Issues pertaining to the documentation are usually marked with the [Documentation](https://github.com/python-poetry/poetry/labels/Documentation) label.

### Contributing to code

#### Picking an issue

{{% note %}}
If you are a first time contributor, and are looking for an issue to take on, you might want to look for [Good First Issue](https://github.com/python-poetry/poetry/issues?q=is%3Aopen+is%3Aissue+label%3A%22Good+First+Issue%22)
labelled issues. We do our best to label such issues, however we might fall behind at times. So, ask us.
{{% /note %}}

If you would like to take on an issue, feel free to comment on the issue tagging `@python-poetry/triage`. We are more than happy to discuss solutions on the issue. If you would like help with navigating
the code base, join us on our [Discord Server](https://discordapp.com/invite/awxPgve).

#### Local development

You will need Poetry to start contributing on the Poetry codebase. Refer to the [documentation](https://python-poetry.org/docs/#introduction) to start using Poetry.

You will first need to clone the repository using `git` and place yourself in its directory:

```bash
$ git clone git@github.com:python-poetry/poetry.git
$ cd poetry
```

{{% note %}}
We recommend that you use a personal [fork](https://docs.github.com/en/free-pro-team@latest/github/getting-started-with-github/fork-a-repo) for this step. If you are new to GitHub collaboration,
you can refer to the [Forking Projects Guide](https://guides.github.com/activities/forking/).
{{% /note %}}

Now, you will need to install the required dependency for Poetry and be sure that the current
tests are passing on your machine:

```bash
$ poetry install
$ poetry run pytest tests/
```

Poetry uses the [black](https://github.com/psf/black) coding style and you must ensure that your
code follows it. If not, the CI will fail and your Pull Request will not be merged.

Similarly, the import statements are sorted with [isort](https://github.com/timothycrosley/isort)
and special care must be taken to respect it. If you don't, the CI will fail as well.

To make sure that you don't accidentally commit code that does not follow the coding style, you can
install a pre-commit hook that will check that everything is in order:

```bash
$ poetry run pre-commit install
```

You can also run it anytime using:

```bash
$ poetry run pre-commit run --all-files
```

Your code must always be accompanied by corresponding tests, if tests are not present your code
will not be merged.

#### Pull requests

* Fill in [the required template](https://github.com/python-poetry/poetry/blob/master/.github/PULL_REQUEST_TEMPLATE.md)
* Be sure that your pull request contains tests that cover the changed or added code.
* If your changes warrant a documentation change, the pull request must also update the documentation.

{{% note %}}
Make sure your branch is [rebased](https://docs.github.com/en/free-pro-team@latest/github/using-git/about-git-rebase) against the latest main branch. A maintainer might ask you to ensure the branch is
up-to-date prior to merging your Pull Request if changes have conflicts.
{{% /note %}}

All pull requests, unless otherwise instructed, need to be first accepted into the main branch (`master`).

### Issue triage

{{% note %}}
If you have an issue that hasn't had any attention, you can ping us `@python-poetry/triage` on the issue. Please, give us reasonable time to get to your issue first, spamming us with messages
{{% /note %}}

If you are helping with the triage of reported issues, this section provides some useful information to assist you in your contribution.

#### Triage steps

1. If `pyproject.toml` is missing or `-vvv` debug logs (with stack trace) is not provided and required, request that the issue author provides it.
1. Attempt to reproduce the issue with the reported Poetry version or request further clarification from the issue author.
1. Ensure the issue is not already resolved. You can attempt to reproduce using the latest preview release and/or poetry from the main branch.
1. If the issue cannot be reproduced,
   1. clarify with the issue's author,
   1. close the issue or notify `@python-poetry/triage`.
1. If the issue can be reproduced,
   1. comment on the issue confirming so
   1. notify `@python-poetry/triage`.
   1. if possible, identify the root cause of the issue.
   1. if interested, attempt to fix it via a pull request.

#### Multiple versions

Often times you would want to attempt to reproduce issues with multiple versions of `poetry` at the same time. For these use cases, the [pipx project](https://pipxproject.github.io/pipx/) is useful.

You can set your environment up like so.

```sh
pipx install --suffix @1.0.10 'poetry==1.0.10'
pipx install --suffix @1.1.0rc1 'poetry==1.1.0rc1'
pipx install --suffix @master 'poetry @ git+https://github.com/python-poetry/poetry'
```

{{% note %}}
Do not forget to update your `poetry@master` installation in sync with upstream.
{{% /note %}}

For `@local` it is recommended that you do something similar to the following as editable installs are not supported for PEP 517 projects.

```sh
# note this will not work for Windows, and we assume you have already run `poetry install`
cd /path/to/python-poetry/poetry
ln -sf $(poetry run which poetry) ~/.local/bin/poetry@local
```

{{% note %}}
This mechanism can also be used to test pull requests.
{{% /note %}}

### Git Workflow

All development work is performed against Poetry's main branch (`master`). All changes are expected to be submitted and accepted to this
branch.

#### Release branch

When a release is ready, the following are required before a release is tagged.

1. A release branch with the prefix `release-`, eg: `release-1.1.0rc1`.
1. A pull request from the release branch to the main branch (`master`) if it's a minor or major release. Otherwise, to the bug fix branch (eg: `1.0`).
   1. The pull request description MUST include the change log corresponding to the release (eg: [#2971](https://github.com/python-poetry/poetry/pull/2971)).
   1. The pull request must contain a commit that updates [CHANGELOG.md](CHANGELOG.md) and bumps the project version (eg: [#2971](https://github.com/python-poetry/poetry/pull/2971/commits/824e7b79defca435cf1d765bb633030b71b9a780)).
   1. The pull request must have the `Release` label specified.

Once the branch pull-request is ready and approved, a member of `@python-poetry/core` will,

1. Tag the branch with the version identifier (eg: `1.1.0rc1`).
2. Merge the pull request once the release is created and assets are uploaded by the CI.

{{% note %}}
In this case, we prefer a merge commit instead of squash or rebase merge.
{{% /note %}}

#### Bug fix branch

Once a minor version (eg: `1.1.0`) is released, a new branch for the minor version (eg: `1.1`) is created for the bug fix releases. Changes identified
or acknowledged by the Poetry team as requiring a bug fix can be submitted as a pull requests against this branch.

At the time of writing only issues meeting the following criteria may be accepted into a bug fix branch. Trivial fixes may be accepted on a
case-by-case basis.

1. The issue breaks a core functionality and/or is a critical regression.
1. The change set does not introduce a new feature or changes an existing functionality.
1. A new minor release is not expected within a reasonable time frame.
1. If the issue affects the next minor/major release, a corresponding fix has been accepted into the main branch.

{{% note %}}
This is subject to the interpretation of a maintainer within the context of the issue.
{{% /note %}}
