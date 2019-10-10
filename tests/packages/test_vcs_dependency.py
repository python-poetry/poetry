from poetry.packages.vcs_dependency import VCSDependency


def test_to_pep_508():
    dependency = VCSDependency(
        "poetry", "git", "https://github.com/sdispater/poetry.git"
    )

    expected = "poetry @ git+https://github.com/sdispater/poetry.git@master"

    assert expected == dependency.to_pep_508()


def test_to_pep_508_with_extras():
    dependency = VCSDependency(
        "poetry", "git", "https://github.com/sdispater/poetry.git"
    )
    dependency.extras.append("foo")

    expected = "poetry[foo] @ git+https://github.com/sdispater/poetry.git@master"

    assert expected == dependency.to_pep_508()


def test_to_pep_508_in_extras():
    dependency = VCSDependency(
        "poetry", "git", "https://github.com/sdispater/poetry.git"
    )
    dependency.in_extras.append("foo")

    expected = (
        'poetry @ git+https://github.com/sdispater/poetry.git@master ; extra == "foo"'
    )
    assert expected == dependency.to_pep_508()

    dependency = VCSDependency(
        "poetry", "git", "https://github.com/sdispater/poetry.git"
    )
    dependency.in_extras.append("foo")
    dependency.extras.append("bar")

    expected = 'poetry[bar] @ git+https://github.com/sdispater/poetry.git@master ; extra == "foo"'

    assert expected == dependency.to_pep_508()

    dependency = VCSDependency(
        "poetry", "git", "https://github.com/sdispater/poetry.git", "b;ar;"
    )
    dependency.in_extras.append("foo;")

    expected = (
        'poetry @ git+https://github.com/sdispater/poetry.git@b;ar; ; extra == "foo;"'
    )

    assert expected == dependency.to_pep_508()
