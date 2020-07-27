#!/bin/sh

set -e

test -n "$PYTHON" || PYTHON="python3"
$PYTHON get-poetry.py -y --preview
$PYTHON $HOME/.poetry/bin/poetry config virtualenvs.create false
$PYTHON $HOME/.poetry/bin/poetry install --no-dev
$PYTHON $HOME/.poetry/bin/poetry run python sonnet make release \
    ${PYTHON27:+-P "2.7:$PYTHON27"} \
    ${PYTHON35:+-P "3.5:$PYTHON35"} \
    ${PYTHON36:+-P "3.6:$PYTHON36"} \
    ${PYTHON37:+-P "3.7:$PYTHON37"} \
    ${PYTHON38:+-P "3.8:$PYTHON38"} \
    ${PYTHON39:+-P "3.9:$PYTHON39"}
