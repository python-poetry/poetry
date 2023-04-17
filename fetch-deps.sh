set -x

rm -fr build
mkdir -p build
VERSION=$(toml2json pyproject.toml | jq '.tool.poetry.version' --raw-output)
POETRY_TAR_FILE="build/poetry-${VERSION}.tar.gz"
tar cz --sort=name --mtime='@1' --exclude="build" --owner=0 --group=0 --numeric-owner -P -f "$POETRY_TAR_FILE" .
pip download "$POETRY_TAR_FILE" -d build
tar czf poetry-bundle.tgz ./build