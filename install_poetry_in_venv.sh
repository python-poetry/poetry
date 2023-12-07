rm -fr poetry_env
poetry build
python -m venv poetry_env
touch poetry_env/poetry_env
poetry_env/bin/pip install dist/poetry-1.5.2-py3-none-any.whl
# need to edit poetry_env/bin/poetry shebang line