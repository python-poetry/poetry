from trove_classifiers import sorted_classifiers


def cli() -> None:
    for classifier in sorted_classifiers:
        print(classifier)


if __name__ == "__main__":
    cli()
