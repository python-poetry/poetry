#
# NOTE: THIS DOCKERFILE IS GENERATED VIA "apply-templates.sh"
#
# PLEASE DO NOT EDIT IT DIRECTLY.
#

FROM python:3.7.13-alpine3.15 as base

ENV POETRY_SCRIPT=https://install.python-poetry.org \
	POETRY_HOME="/opt/poetry"

ENV POETRY_CACHE_DIR="$POETRY_HOME/.cache" \
    XDG_CACHE_HOME="$POETRY_HOME/.cache"
    # POETRY_CACHE_DIR is not respected currently see https://github.com/python-poetry/poetry/issues/2445#issuecomment-670829271

ENV PATH="$PATH:$POETRY_HOME/bin"

FROM base as builder

SHELL ["/bin/ash", "-eo", "pipefail", "-c"]

RUN apk add --no-cache gcc musl-dev libffi-dev \
	&& wget -q -O- "$POETRY_SCRIPT" | python

FROM base as runtime

RUN apk add --no-cache libffi

COPY --from=builder $POETRY_HOME $POETRY_HOME

CMD ["poetry"]
