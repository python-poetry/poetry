---
title: "Docker Best Practices"
draft: true
type: docs
layout: "docs"

menu:
  docs:
    weight: 50
---

# Docker Best Practices

## Introduction

....blabla
The following best practices should be kept in mind

- [optional] set the latest python version, in order to get the latest patch
- [highly suggested] use pip to install poetry
- [critical] never hardcode credentials to private sources
- ...

## Use cases

The following are general use cases that you can use a starting point for your specific case

### UC1: Dev environment

Here is an example of how to create a dev container aimed to host a basic development env. Once the image is built nobody can make OS changes, except the admin. An example of usage is a container used by a team.

#### Specifics

- Unprivileged User.
- multistage, in order to make the image lighter
- ...

#### Dockerfile

FROM python .......
....