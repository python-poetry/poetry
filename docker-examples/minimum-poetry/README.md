# Minimum Poetry image

## Description

Minimum-poetry is the minimum-constructible image containing poetry, from an official python base image.

Expected size: ~218 MB, virtual env layer excluded.

## Use cases

This image is especially useful when you don't yet have in mind a clear idea of the environment requirements you need, but need a reproducible first starting point for a python development environment. It' a quick and easy way to start.

## How to use it

Run the following commmands from the *minimum-poetry* folder. They are just an example of how to use it. You can wrrite your custom commands according to Docker API. For more information about Docker please see the [official documentation](https://docs.docker.com/).

### Build the image

```bash
# This will build the image

TAG="minimum-poetry:0.1.0"
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
