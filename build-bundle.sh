# Generate a bundle containing poetry + dependencies
# for use by Nix using pip's download command to allow offline installs as
# described here: https://stackoverflow.com/a/36730026

# The generated file is to be uploaded to the poetry-bundles bucket on gcs, available at
# https://storage.googleapis.com/poetry-bundles/poetry-x.y.z-bundle.tgz

# You may use `nix develop` to gain access the tools used by this script.

set -x

BUILD_DIR=poetry-bundle

rm -fr $BUILD_DIR
mkdir -p $BUILD_DIR
VERSION=$(toml2json pyproject.toml | jq '.tool.poetry.version' --raw-output)
POETRY_TAR_FILE="poetry-${VERSION}.tgz"
tar cz --sort=name --mtime='@1' --exclude="$BUILD_DIR" --exclude="$POETRY_TAR_FILE" --owner=0 --group=0 --numeric-owner -P -f "$POETRY_TAR_FILE" .
pip download "$POETRY_TAR_FILE" -d $BUILD_DIR
tar czf poetry-${VERSION}-bundle.tgz $BUILD_DIR
rm "$POETRY_TAR_FILE"
rm -fr "$BUILD_DIR"