FROM python:3.6

# install poetry 
RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

# create application directory 
RUN mkdir /app
WORKDIR /app

RUN poetry config settings.virtualenvs.create false

# copy pyproject file(s)
ONBUILD COPY pyproject.* .

# install dependencies
ONBUILD RUN poetry install -n
