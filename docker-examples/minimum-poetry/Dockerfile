FROM python:3.11-slim

ARG POETRY_VERSION=1.8

# See https://python-poetry.org/docs/#ci-recommendations
RUN pip install "poetry==${POETRY_VERSION}"

WORKDIR /app

# --- Reproduce the environment ---
# You can comment the following two lines if you prefer to manually install
#   the dependencies from inside the container.
COPY pyproject.toml .

RUN poetry install
# --- --- --- --- --- --- --- --- ---

ENTRYPOINT ["bash"]
