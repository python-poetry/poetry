#!/bin/sh

set -ex

RUNTIMES[0]="${PYTHON27:+-P "2.7:$PYTHON27"}"
RUNTIMES[1]="${PYTHON35:+-P "3.5:$PYTHON35"}"
RUNTIMES[2]="${PYTHON36:+-P "3.6:$PYTHON36"}"
RUNTIMES[3]="${PYTHON37:+-P "3.7:$PYTHON37"}"
RUNTIMES[4]="${PYTHON38:+-P "3.8:$PYTHON38"}"

test -n "$PYTHON" || PYTHON="python3"

if [ "$OSTYPE" == "linux-gnu" ]; then
  $PYTHON get-poetry.py -y
  POETRY="$PYTHON $HOME/.poetry/bin/poetry"
  RUNTIMES[5]="${PYTHON39:+-P "3.9:$PYTHON39"}"
  RUNTIMES[6]="${PYTHON310:+-P "3.10:$PYTHON310"}"
else
  $PYTHON -m pip install poetry -U
  POETRY="$PYTHON -m poetry"
fi

$POETRY config virtualenvs.in-project true
$POETRY install --no-dev
$POETRY run python sonnet make release ${RUNTIMES[@]}
