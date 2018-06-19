FROM python:3.6

# install poetry and disable virtualenvs creations
RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python && \
    poetry config settings.virtualenvs.create false

WORKDIR /app

# copy pyproject file(s)
ONBUILD COPY pyproject.* .

# install dependencies
ONBUILD RUN poetry install -n
