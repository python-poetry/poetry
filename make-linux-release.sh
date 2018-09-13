#!/bin/bash
PYTHON_VERSIONS="cp27-cp27m cp34-cp34m cp35-cp35m cp36-cp36m cp37-cp37m"

cd /io
/opt/python/cp37-cp37m/bin/pip install poetry --pre -U
/opt/python/cp37-cp37m/bin/poetry config settings.virtualenvs.create false
/opt/python/cp37-cp37m/bin/poetry install --no-dev
/opt/python/cp37-cp37m/bin/python sonnet make:release \
    -P "2.7:/opt/python/cp27-cp27m/bin/python" \
    -P "3.4:/opt/python/cp34-cp34m/bin/python" \
    -P "3.5:/opt/python/cp35-cp35m/bin/python" \
    -P "3.6:/opt/python/cp36-cp36m/bin/python" \
    -P "3.7:/opt/python/cp37-cp37m/bin/python"
cd -
