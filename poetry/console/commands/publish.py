from .command import Command


class PublishCommand(Command):
    """
    Publishes a package to a remote repository.

    publish
        { --r|repository= : The repository to publish the package to. }
        { --u|username= : The username to access the repository. }
        { --p|password= : The password to access the repository. }
        { --no-build : Do not build the package before publishing. }
    """

    help = """The publish command builds and uploads the package to a remote repository.

By default, it will upload to PyPI but if you pass the --repository option it will
upload to it instead.

The --repository option should match the name of a configured repository using
the config command.
"""

    def handle(self):
        from poetry.masonry.publishing.publisher import Publisher

        # Building package first, unless told otherwise
        if not self.option('no-build'):
            self.call('build')

        self.line('')

        publisher = Publisher(self.poetry, self.output)
        publisher.publish(
            self.option('repository'),
            self.option('username'),
            self.option('password')
        )
