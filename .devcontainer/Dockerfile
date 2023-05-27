
ARG IMAGE="python:3.11"
FROM --platform=amd64 mcr.microsoft.com/vscode/devcontainers/${IMAGE}
RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends build-essential libssl-dev gdb cmake

ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python3 -
