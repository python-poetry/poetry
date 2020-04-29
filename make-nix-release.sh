#!/bin/sh

set -e

test -n "$PYTHON" || PYTHON="python3"
$PYTHON -m pip install pip -U
$PYTHON -m pip install poetry -U --pre
$PYTHON -m poetry config virtualenvs.create false
$PYTHON -m poetry install --no-dev
$PYTHON sonnet make release \
    ${PYTHON27:+-P "2.7:$PYTHON27"} \
    ${PYTHON35:+-P "3.5:$PYTHON35"} \
    ${PYTHON36:+-P "3.6:$PYTHON36"} \
    ${PYTHON37:+-P "3.7:$PYTHON37"} \
    ${PYTHON38:+-P "3.8:$PYTHON38"}
