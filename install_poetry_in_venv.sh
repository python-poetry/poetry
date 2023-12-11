# This script installs poetry within its own venv the way
# it is when deployed so that its deps are isolated from the deps of the projects it manages
rm -fr poetry_env
poetry build
python -m venv poetry_env
touch poetry_env/poetry_env
poetry_env/bin/pip install dist/poetry-1.5.2-py3-none-any.whl
# inspired by https://stackoverflow.com/a/584926:
sed -i 's@/usr/bin/env python3@'"$REPL_HOME"'/poetry_env/bin/python3@g' poetry_env/bin/poetry