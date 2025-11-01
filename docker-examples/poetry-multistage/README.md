# Minimum Poetry multistage image

## Description

poetry-multistage is a minimum-constructible multistage image containing Poetry, from an official Python base image.

Expected size: ~130MB, virtual env layer excluded.

## Use cases

The usefulness of this image lies in the Dockerfile that shows an example of how to build a multistage image, to optimize the construction of the virtual environment. Always use it as a starting point for your images that you want to optimize in size.

## How to use it

Run the following commmands from the *poetry-multistage* folder. They are just an example of how to use it. You can wrrite your custom commands according to Docker API. For more information about Docker please see the [official documentation](https://docs.docker.com/).

### Build the image

```bash
# This will build the image

TAG="poetry-multistage:0.1.0"
docker build \
    -t $TAG \
    --build-arg POETRY_VERSION="1.8.3" \
    "."
```

### Run the container

```bash
# This will run the container

docker run \
    --rm -it \
    -v ${PWD}:/app/shared \
    "$TAG"
```
