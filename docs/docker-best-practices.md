---
title: "Docker Best Practices"
draft: false
type: docs
layout: "docs"

menu:
  docs:
    weight: 130
---

# Docker Best Practices

Poetry is a very valuable tool for increasing the robustness and reproducibility of a virtual environment on which your python code is based. When integrating Poetry into a Docker image, adopting some best practices will help improve build efficiency, container security, and help achieve lighter images. In this section, we will explore best practices for creating optimized and secure Docker images for projects managed with Poetry.
This section is a developing project, so you are warmly invited to contribute new suggestions.

## Best Practices

The following best practices should be kept in mind

- [optional] Set the latest python version, in order to get the latest security patch.
  - CAVEAT: It might reduce the reproducibility of the code, between one image build and another, since some function might change from one version of python to another.
- [highly suggested] Use `pip` to install Poetry (see [CI recommendations]({{< ref "#ci-recommendations" >}})).
- [highly suggested] Use [Docker cache mounts](https://docs.docker.com/build/cache/optimize/#use-cache-mounts) to reuse the Poetry installation cache and speed up builds.
  - Or alternatively: clear Poetry cache after the installation.
- [critical] Never hardcode credentials to private sources.
- [optional] Install Poetry in a dedicated venv
- [highly suggested] Install the virtual env in the Python project (see `POETRY_VIRTUALENVS_IN_PROJECT`). This will be more convenient for carrying the env around with everything you need, making the project more self-contained.
- [highly suggested] Take advantage of Docker's layer caching mechanism to rebuild the image much faster. This means that you should reduce the variability points in the Dockerfile and the files linked to it (e.g. ARGS that may change). In alternative you can move them as far down in the Dockerfile as possible. For more info please see:
  - https://docs.docker.com/build/cache/
  - https://pythonspeed.com/docker/
- [highly suggested] copy source code only after `poetry install`. For more info see: [FAQ]({{< relref "faq/#poetry-busts-my-docker-cache-because-it-requires-me-to-copy-my-source-files-in-before-installing-3rd-party-dependencies" >}})

## Images examples and use cases

Below are general examples of Docker images, along with their typical use cases, to help you get started with developing your specific application.

### Minimum-poetry

[Minimum-poetry](https://github.com/gianfa/poetry/tree/docs/docker-best-practices/docker-examples/minimum-poetry/README.md) is the minimum-constructible image containing poetry, from an official python base image.

Expected size: ~218 MB, virtual env layer excluded.

#### Specifics

- Based on *python:3.11-slim* official image.
- Just installs Poetry via pip.
- A basic virtual environment is created passing a pyproject.toml, via build context.

#### Use cases

As in the case of [Minimum-poetry](https://github.com/gianfa/poetry/tree/docs/docker-best-practices/docker-examples/minimum-poetry/README.md), this image is useful when you need to create a virtual self-content  environment, complex at will.

### Poetry-multistage

[Poetry-multistage](https://github.com/gianfa/poetry/tree/docs/docker-best-practices/docker-examples/poetry-multistage/README.md) is a minimum-constructible multistage image containing Poetry, from an official Python base image. It is very similar to [Minimum-poetry](#minimum-poetry), except that it may be more complex as it implements at least 2 more best practices.

Expected size: ~130MB, virtual env layer excluded.

#### Specifics

- Based on *python:3.11-slim* official image.
- Installs Poetry via pip.
- A basic virtual environment is created in the project folder (`POETRY_VIRTUALENVS_IN_PROJECT=1`, `POETRY_VIRTUALENVS_CREATE=1`).
- A multistage build is implemented, allowing you to directly copy only the project virtual env and set its reference in path, so as to minimize memory waste.

#### Use cases

The usefulness of this image lies in the Dockerfile that shows an example of how to build a multistage image, to optimize the construction of the virtual environment. Always use it as a starting point for your images that you want to optimize in size.
