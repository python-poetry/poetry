# Change Log

## [Unreleased]

### Added

- Added a `debug:info` command to get information about current environment.

### Fixed

- Fixed Python version retrieval inside virtualenvs.
- Fixed optional dependencies being set as required in sdist.


## [0.6.3] - 2018-03-20

### Fixed

- Fixed built wheels not getting information from the virtualenv.
- Fixed building wheel with conditional extensions.
- Fixed missing files in built wheel with extensions.
- Fixed call to venv binaries on windows.
- Fixed subdependencies representation in lock file.


## [0.6.2] - 2018-03-19

### Changed

- Changed how wilcard constraints are handled.

### Fixed

- Fixed errors with pip 9.0.2.


## [0.6.1] - 2018-02-18

### Fixed

- Fixed wheel entry points being written on a single line.
- Fixed wheel metadata (Tag and Root-Is-Purelib).


## [0.6.0] - 2018-03-16

### Added

- Added support for virtualenv autogeneration (Python 3.6+ only).
- Added the `run` command to execute commands inside the created virtualenvs.
- Added the `debug:resolve` command to debug dependency resolution.
- Added `pyproject.toml` file validation.
- Added support for Markdown readme files.

### Fixed

- Fixed color displayed in `show` command for semver-compatible updates.
- Fixed Python requirements in publishing metadata.
- Fixed `update` command reinstalling every dependency.


## [0.5.0] - 2018-03-14

### Added

- Added experimental support for package with C extensions.

### Changed

- Added hashes check when installing packages.

### Fixed

- Fixed handling of post releases.
- Fixed python restricted dependencies not being checked against virtualenv version.
- Fixed python/platform constraint not being picked up for subdependencies.
- Fixed skipped packages appearing as installing.
- Fixed platform specification not being used when resolving dependencies.


## [0.4.2] - 2018-03-10

### Fixed

- Fixed TypeError when `requires_dist` is null on PyPI.


## [0.4.1] - 2018-03-08

### Fixed

- Fixed missing entry point


## [0.4.0] - 2018-03-08

### Added

- Added packaging support (sdist and pure-python wheel).
- Added the `build` command.
- Added support for extras definition.
- Added support for dependencies extras specification.
- Added the `config` command.
- Added the `publish` command.

### Changed

- Dependencies system constraints are now respected when installing packages.
- Complied with PEP 440

### Fixed

- Fixed `show` command for VCS dependencies.
- Fixed handling of releases with bad markers in PyPiRepository.


## [0.3.0] - 2018-03-05

### Added

- Added `show` command. 
- Added the `--dry-run` option to the `add` command.

### Changed

- Changed the `poetry.toml` file for the new, standardized `pyproject.toml`.
- Dependencies of each package is now stored in the lock file.
- Improved TOML file management.
- Dependency resolver now respects the root package python version requirements.

### Fixed

- Fixed the `add` command for packages with dots in their names.


## [0.2.0] - 2018-03-01

### Added

- Added `remove` command.
- Added basic support for VCS (git) dependencies.
- Added support for private repositories.

### Changed

- Changed `poetry.lock` format.

### Fixed

- Fixed dependencies solving that would lead to dependencies not being written to lock.


## [0.1.0] - 2018-02-28

Initial release



[Unreleased]: https://github.com/sdispater/poetry/compare/0.6.3...master
[0.6.3]: https://github.com/sdispater/poetry/releases/tag/0.6.3
[0.6.2]: https://github.com/sdispater/poetry/releases/tag/0.6.2
[0.6.1]: https://github.com/sdispater/poetry/releases/tag/0.6.1
[0.6.0]: https://github.com/sdispater/poetry/releases/tag/0.6.0
[0.5.0]: https://github.com/sdispater/poetry/releases/tag/0.5.0
[0.4.2]: https://github.com/sdispater/poetry/releases/tag/0.4.2
[0.4.1]: https://github.com/sdispater/poetry/releases/tag/0.4.1
[0.4.0]: https://github.com/sdispater/poetry/releases/tag/0.4.0
[0.3.0]: https://github.com/sdispater/poetry/releases/tag/0.3.0
[0.2.0]: https://github.com/sdispater/poetry/releases/tag/0.2.0
[0.1.0]: https://github.com/sdispater/poetry/releases/tag/0.1.0
