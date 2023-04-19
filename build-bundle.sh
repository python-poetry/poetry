set -x

BUILD_DIR=poetry-bundle

rm -fr $BUILD_DIR
mkdir -p $BUILD_DIR
VERSION=$(toml2json pyproject.toml | jq '.tool.poetry.version' --raw-output)
POETRY_TAR_FILE="poetry-${VERSION}.tgz"
tar cz --sort=name --mtime='@1' --exclude="$BUILD_DIR" --owner=0 --group=0 --numeric-owner -P -f "$POETRY_TAR_FILE" .
pip download "$POETRY_TAR_FILE" -d $BUILD_DIR
tar czf poetry-${VERSION}-bundle.tgz $BUILD_DIR