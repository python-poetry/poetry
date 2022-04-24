#
# NOTE: THIS DOCKERFILE IS GENERATED VIA "apply-templates.sh"
#
# PLEASE DO NOT EDIT IT DIRECTLY.
#

FROM python:3.10.4-windowsservercore-1809

ENV POETRY_SCRIPT=https://install.python-poetry.org \
	POETRY_HOME="C:/poetry"

ENV POETRY_CACHE_DIR="$POETRY_HOME/.cache" \
    XDG_CACHE_HOME="$POETRY_HOME/.cache"
    # POETRY_CACHE_DIR is not respected currently see https://github.com/python-poetry/poetry/issues/2445#issuecomment-670829271

RUN [Environment]::SetEnvironmentVariable('PATH', $env:POETRY_HOME + '/bin;' + $env:PATH, [EnvironmentVariableTarget]::Machine); \
    (Invoke-WebRequest -Uri $env:POETRY_SCRIPT -UseBasicParsing).Content | python -

CMD ["poetry"]
