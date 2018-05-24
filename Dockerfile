FROM python:3.6

# install poetry
RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

# disable virtualenvs creations
RUN poetry config settings.virtualenvs.create false

# create application directory
RUN mkdir /app
WORKDIR /app

# copy pyproject file(s)
ONBUILD COPY pyproject.* .

# install dependencies
ONBUILD RUN poetry install -n
