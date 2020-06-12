from poetry.packages.url_dependency import URLDependency


EXAMPLE_URL = (
    "https://github.com/python-poetry/poetry/releases/"
    "download/1.0.9/poetry-1.0.9-linux.tar.gz"
)


def test_to_pep_508():
    dependency = URLDependency("poetry", EXAMPLE_URL,)

    expected = "poetry @ {}".format(EXAMPLE_URL)

    assert expected == dependency.to_pep_508()


def test_to_pep_508_in_extras():
    dependency = URLDependency("poetry", EXAMPLE_URL,)
    dependency.in_extras.append("foo")

    expected = 'poetry @ {} ; extra == "foo"'.format(EXAMPLE_URL)
    assert expected == dependency.to_pep_508()
