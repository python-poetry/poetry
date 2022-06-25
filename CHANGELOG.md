# Change Log

## [1.2.0b2] - 2022-06-07

### Added

- Added support for multiple-constraint direct origin dependencies with the same
  version ([#5715](https://github.com/python-poetry/poetry/pull/5715))
- Added support disabling TLS verification for custom package sources via `poetry config certificates.<repository>.cert false` ([#5719](https://github.com/python-poetry/poetry/pull/5719)
- Added new configuration (`virtualenvs.prompt`) to customize the prompt of the Poetry-managed virtual environment ([#5606](https://github.com/python-poetry/poetry/pull/5606))
- Added progress indicator to `download_file` (used when downloading dists) ([#5451](https://github.com/python-poetry/poetry/pull/5451))
- Added `--dry-run` to `poetry version` command ([#5603](https://github.com/python-poetry/poetry/pull/5603))
- Added `--why` to `poetry show` ([#5444](https://github.com/python-poetry/poetry/pull/5444))
- Added support for single page (html) repositories ([#5517](https://github.com/python-poetry/poetry/pull/5517))
- Added support for PEP 508 strings when adding
  dependencies via `poetry add` command ([#5554](https://github.com/python-poetry/poetry/pull/5554))
- Added `--no-cache` as a global option ([#5519](https://github.com/python-poetry/poetry/pull/5519))
- Added cert retrieval for HTTP requests made by Poetry ([#5320](https://github.com/python-poetry/poetry/pull/5320))
- Added `--skip-existing` to `poetry publish` ([#2812](https://github.com/python-poetry/poetry/pull/2812))
- Added `--all-extras` to `poetry install` ([#5452](https://github.com/python-poetry/poetry/pull/5452))
- Added new `poetry self` sub-commands to manage plugins and/or system environment packages, eg: keyring backends ([#5450](https://github.com/python-poetry/poetry/pull/5450))
- Added new configuration (`installer.no-binary`) to allow selection of non-binary distributions when installing a dependency ([#5609](https://github.com/python-poetry/poetry/pull/5609))

### Changed

- `poetry plugin` commands are now deprecated in favor of the more generic `poetry self`
  commands ([#5450](https://github.com/python-poetry/poetry/pull/5450))
- When creating new projects, Poetry no longer restricts README extensions to `md` and `rst` ([#5357](https://github.com/python-poetry/poetry/pull/5357))
- Changed the provider to allow fallback to installed packages ([#5704](https://github.com/python-poetry/poetry/pull/5704))
- Solver now correctly handles and prefers direct reference constraints (vcs, file etc.) over public version identifiers ([#5654](https://github.com/python-poetry/poetry/pull/5654))
- Changed the build script behavior to create an ephemeral build environment when a build script is
  specified ([#5401](https://github.com/python-poetry/poetry/pull/5401))
- Improved performance when determining PEP 517 metadata from sources ([#5601](https://github.com/python-poetry/poetry/pull/5601))
- Project package sources no longer need to be redefined as global repositories when configuring credentials ([#5563](https://github.com/python-poetry/poetry/pull/5563))
- Replaced external git command use with dulwich, in order to force the legacy behaviour set `experimental.system-git-client` configuration to `true` ([#5428](https://github.com/python-poetry/poetry/pull/5428))
- Improved http request handling for sources and multiple paths on same netloc ([#5518](https://github.com/python-poetry/poetry/pull/5518))
- Made `no-pip` and `no-setuptools` configuration explicit ([#5455](https://github.com/python-poetry/poetry/pull/5455))
- Improved application logging, use of `-vv` now provides more debug information ([#5503](https://github.com/python-poetry/poetry/pull/5503))
- Renamed implicit group `default` to `main` ([#5465](https://github.com/python-poetry/poetry/pull/5465))
- Replaced in-tree implementation of `poetry export`
  with `poetry-plugin-export` ([#5413](https://github.com/python-poetry/poetry/pull/5413))
- Changed the password manager behavior to use a `"null"` keyring when
  disabled ([#5251](https://github.com/python-poetry/poetry/pull/5251))
- Incremental improvement of Solver performance ([#5335](https://github.com/python-poetry/poetry/pull/5335))
- Newly created virtual environments on macOS now are excluded from Time Machine backups ([#4599](https://github.com/python-poetry/poetry/pull/4599))
- Poetry no longer raises an exception when a package is not found on PyPI ([#5698](https://github.com/python-poetry/poetry/pull/5698))
- Update `packaging` dependency to use major version 21, this change forces Poetry to drop support for managing Python 2.7 environments ([#4749](https://github.com/python-poetry/poetry/pull/4749))

### Fixed

- Fixed `poetry update --dry-run` to not modify `poetry.lock` ([#5718](https://github.com/python-poetry/poetry/pull/5718), [#3666](https://github.com/python-poetry/poetry/issues/3666), [#3766](https://github.com/python-poetry/poetry/issues/3766))
- Fixed [#5537](https://github.com/python-poetry/poetry/issues/5537) where export fails to resolve dependencies with more than one
  path ([#5688](https://github.com/python-poetry/poetry/pull/5688))
- Fixed an issue where the environment variables `POETRY_CONFIG_DIR` and `POETRY_CACHE_DIR` were not being respected ([#5672](https://github.com/python-poetry/poetry/pull/5672))
- Fixed [#3628](https://github.com/python-poetry/poetry/issues/3628) and [#4702](https://github.com/python-poetry/poetry/issues/4702) by handling invalid distributions
  gracefully ([#5645](https://github.com/python-poetry/poetry/pull/5645))
- Fixed an issue where the provider ignored subdirectory when merging and improve subdirectory support for vcs
  deps ([#5648](https://github.com/python-poetry/poetry/pull/5648))
- Fixed an issue where users could not select an empty choice when selecting
  dependencies ([#4606](https://github.com/python-poetry/poetry/pull/4606))
- Fixed an issue where `poetry init -n` crashes in a root directory ([#5612](https://github.com/python-poetry/poetry/pull/5612))
- Fixed an issue where Solver errors arise due to wheels having different Python
  constraints ([#5616](https://github.com/python-poetry/poetry/pull/5616))
- Fixed an issue where editable path dependencies using `setuptools` could not be correctly installed ([#5590](https://github.com/python-poetry/poetry/pull/5590))
- Fixed flicker when displaying executor operations ([#5556](https://github.com/python-poetry/poetry/pull/5556))
- Fixed an issue where the `poetry lock --no-update` only sorted by name and not by name and
  version ([#5446](https://github.com/python-poetry/poetry/pull/5446))
- Fixed an issue where the Solver fails when a dependency has multiple constrained dependency definitions for the same
  package ([#5403](https://github.com/python-poetry/poetry/pull/5403))
- Fixed an issue where dependency resolution takes a while because Poetry checks all possible combinations
  even markers are mutually exclusive ([#4695](https://github.com/python-poetry/poetry/pull/4695))
- Fixed incorrect version selector constraint ([#5500](https://github.com/python-poetry/poetry/pull/5500))
- Fixed an issue where `poetry lock --no-update` dropped
  packages ([#5435](https://github.com/python-poetry/poetry/pull/5435))
- Fixed an issue where packages were incorrectly grouped when
  exporting ([#5156](https://github.com/python-poetry/poetry/pull/5156))
- Fixed an issue where lockfile always updates when using private
  sources ([#5362](https://github.com/python-poetry/poetry/pull/5362))
- Fixed an issue where the solver did not account for selected package features ([#5305](https://github.com/python-poetry/poetry/pull/5305))
- Fixed an issue with console script execution of editable dependencies on Windows ([#3339](https://github.com/python-poetry/poetry/pull/3339))
- Fixed an issue where editable builder did not write PEP-610 metadata ([#5703](https://github.com/python-poetry/poetry/pull/5703))
- Fixed an issue where Poetry 1.1 lock files were incorrectly identified as not fresh ([#5458](https://github.com/python-poetry/poetry/pull/5458))

### Docs

- Updated plugin management commands ([#5450](https://github.com/python-poetry/poetry/pull/5450))
- Added the `--readme` flag to documentation ([#5357](https://github.com/python-poetry/poetry/pull/5357))
- Added example for multiple maintainers ([#5661](https://github.com/python-poetry/poetry/pull/5661))
- Updated documentation for issues [#4800](https://github.com/python-poetry/poetry/issues/4800), [#3709](https://github.com/python-poetry/poetry/issues/3709), [#3573](https://github.com/python-poetry/poetry/issues/3573), [#2211](https://github.com/python-poetry/poetry/issues/2211) and [#2414](https://github.com/python-poetry/poetry/pull/2414) ([#5656](https://github.com/python-poetry/poetry/pull/5656))
- Added `poetry.toml` note in configuration ([#5492](https://github.com/python-poetry/poetry/pull/5492))
- Add documentation for `poetry about`, `poetry help`, `poetrylist`, and the `--full-path` and `--all` options
  documentation ([#5664](https://github.com/python-poetry/poetry/pull/5664))
- Added more clarification to the `--why` flag ([#5653](https://github.com/python-poetry/poetry/pull/5653))
- Updated documentation to refer to PowerShell for Windows, including
  instructions ([#3978](https://github.com/python-poetry/poetry/pull/3978), [#5618](https://github.com/python-poetry/poetry/pull/5618))
- Added PEP 508 name requirement ([#5642](https://github.com/python-poetry/poetry/pull/5642))
- Added example for each section of pyproject.toml ([#5585](https://github.com/python-poetry/poetry/pull/5642))
- Added documentation for `--local` to fix issue [#5623](https://github.com/python-poetry/poetry/issues/5623) ([#5629](https://github.com/python-poetry/poetry/pull/5629))
- Added troubleshooting documentation for using proper quotation with
  ZSH ([#4847](https://github.com/python-poetry/poetry/pull/4847))
- Added information on git and basic http auth ([#5578](https://github.com/python-poetry/poetry/pull/5578))
- Removed ambiguity about PEP 440 and semver ([#5576](https://github.com/python-poetry/poetry/pull/5576))
- Removed Pipenv comparison ([#5561](https://github.com/python-poetry/poetry/pull/5561))
- Improved dependency group related documentation ([#5338](https://github.com/python-poetry/poetry/pull/5338))
- Added documentation for default directories used by Poetry ([#5391](https://github.com/python-poetry/poetry/pull/5301))
- Added warning about credentials preserved in shell history ([#5726](https://github.com/python-poetry/poetry/pull/5726))
- Improved documentation of the `readme` option, including multiple files and additional formats ([#5158](https://github.com/python-poetry/poetry/pull/5158))
- Improved contributing documentation ([#5708](https://github.com/python-poetry/poetry/pull/5708))
- Remove all references to `--dev-only` option ([#5771](https://github.com/python-poetry/poetry/pull/5771))
- Added environment variable checking for PyPi token ([#5911](https://github.com/python-poetry/poetry/pull/5911))


## [1.2.0b1] - 2022-03-17

### Fixed

- Fixed an issue where the system environment couldn't be detected ([#4406](https://github.com/python-poetry/poetry/pull/4406)).
- Fixed another issue where the system environment couldn't be detected ([#4433](https://github.com/python-poetry/poetry/pull/4433)).
- Replace deprecated requests parameter in uploader ([#4580](https://github.com/python-poetry/poetry/pull/4580)).
- Fix an issue where venv are detected as broken when using MSys2 on windows ([#4482](https://github.com/python-poetry/poetry/pull/4482)).
- Fixed an issue where the cache breaks on windows ([#4531](https://github.com/python-poetry/poetry/pull/4531)).
- Fixed an issue where a whitespace before a semicolon was missing on `poetry export` ([#4575](https://github.com/python-poetry/poetry/issues/4575)).
- Fixed an issue where markers were not correctly assigned to nested dependencies ([#3511](https://github.com/python-poetry/poetry/issues/3511)).
- Recognize one digit version in wheel filenames ([#3338](https://github.com/python-poetry/poetry/pull/3338)).
- Fixed an issue when `locale` is unset ([#4038](https://github.com/python-poetry/poetry/pull/4038)).
- Fixed an issue where the fallback to another interpreter didn't work ([#3475](https://github.com/python-poetry/poetry/pull/3475)).
- Merge any marker constraints into constraints with specific markers ([#4590](https://github.com/python-poetry/poetry/pull/4590)).
- Normalize path before hashing so that the generated venv name is independent of case on Windows ([#4813](https://github.com/python-poetry/poetry/pull/4813)).
- Fixed an issue where a dependency wasn't upgrade by using `@latest` on `poetry update` ([#4945](https://github.com/python-poetry/poetry/pull/4945)).
- Fixed an issue where conda envs in windows are always reported as broken([#5007](https://github.com/python-poetry/poetry/pull/5007)).
- Fixed an issue where Poetry doesn't find its own venv on `poetry self update` ([#5049](https://github.com/python-poetry/poetry/pull/5049)).
- Fix misuse of pretty_constraint ([#4932](https://github.com/python-poetry/poetry/pull/4932)).
- Fixed an issue where the reported python version used for venv creation wasn't correct ([#5086](https://github.com/python-poetry/poetry/pull/5086)).
- Fixed an issue where the searched package wasn't display in the interactive dialog of `poetry init` ([#5076](https://github.com/python-poetry/poetry/pull/5076)).
- Fixed an issue where Poetry raises an exception on `poetry show` when no lock files exists ([#5242](https://github.com/python-poetry/poetry/pull/5242)).
- Fixed an issue where Poetry crashes when optional `vcs_info.requested_version` in `direct_url.json` wasn't included ([#5274](https://github.com/python-poetry/poetry/pull/5274)).
- Fixed an issue where dependencies with extras were updated despite using `--no-update` ([#4618](https://github.com/python-poetry/poetry/pull/4618)).
- Fixed various places where poetry writes messages to stdout instead of stderr ([#4110](https://github.com/python-poetry/poetry/pull/4110), [#5179](https://github.com/python-poetry/poetry/pull/5179)).
- Ensured that when complete packages are created dependency inherits source and resolved refs from package ([#4604](https://github.com/python-poetry/poetry/pull/4604)).
- Ensured that when complete packages are created dependency inherits subdirectory from package if supported ([#4604](https://github.com/python-poetry/poetry/pull/4604)).
- Fixed an issue where `POETRY_EXPERIMENTAL_NEW_INSTALLER` needs to be set to an empty string to disable it ([#3811](https://github.com/python-poetry/poetry/pull/3811)).

### Added

- `poetry show <package>` now also shows which packages depend on it ([#2351](https://github.com/python-poetry/poetry/pull/2351)).
- The info dialog by `poetry about` now contains version information about installed poetry and poetry-core ([#5288](https://github.com/python-poetry/poetry/pull/5288)).
- Print error message when `poetry publish` fails ([#3549](https://github.com/python-poetry/poetry/pull/3549)).
- Added in info output to `poetry lock --check` ([#5081](https://github.com/python-poetry/poetry/pull/5081)).
- Added new argument `--all` for `poetry env remove` to delete all venv of a project at once ([#3212](https://github.com/python-poetry/poetry/pull/3212)).
- Added new argument `--without-urls` for `poetry export` to exclude source repository urls from the exported file ([#4763](https://github.com/python-poetry/poetry/pull/4763)).
- Added a `new installer.max-workers` property to the configuration ([#3516](https://github.com/python-poetry/poetry/pull/3516)).
- Added experimental option `virtualenvs.prefer-active-python` to detect current activated python ([#4852](https://github.com/python-poetry/poetry/pull/4852)).
- Added better windows shell support ([#5053](https://github.com/python-poetry/poetry/pull/5053)).

### Changed

- Drop python3.6 support ([#5055](https://github.com/python-poetry/poetry/pull/5055)).
- Exit with callable return code in generated script ([#4456](https://github.com/python-poetry/poetry/pull/4456)).
- Internal use of the `pep517` high level interfaces for package metadata inspections have been replaced with the `build` package. ([#5155](https://github.com/python-poetry/poetry/pull/5155)).
- Poetry now raises an error if the python version in the project environment is no longer compatible with the project ([#4520](https://github.com/python-poetry/poetry/pull/4520)).


## [1.1.13] - 2022-02-09

### Fixed

- Fixed an issue where envs in MSYS2 always reported as broken ([#4942](https://github.com/python-poetry/poetry/pull/4942))
- Fixed an issue where conda envs in windows are always reported as broken([#5008](https://github.com/python-poetry/poetry/pull/5008))
- Fixed an issue where Poetry doesn't find its own venv on `poetry self update` ([#5048](https://github.com/python-poetry/poetry/pull/5048))

## [1.1.12] - 2021-11-27

### Fixed

- Fixed broken caches on Windows due to `Path` starting with a slash ([#4549](https://github.com/python-poetry/poetry/pull/4549))
- Fixed `JSONDecodeError` when installing packages by updating `cachecontrol` version ([#4831](https://github.com/python-poetry/poetry/pull/4831))
- Fixed dropped markers in dependency walk ([#4686](https://github.com/python-poetry/poetry/pull/4686))

## [1.1.11] - 2021-10-04

### Fixed

- Fixed errors when installing packages on Python 3.10. ([#4592](https://github.com/python-poetry/poetry/pull/4592))
- Fixed an issue where the wrong `git` executable could be used on Windows. ([python-poetry/poetry-core#213](https://github.com/python-poetry/poetry-core/pull/213))
- Fixed an issue where the Python 3.10 classifier was not automatically added. ([python-poetry/poetry-core#215](https://github.com/python-poetry/poetry-core/pull/215))

## [1.1.10] - 2021-09-21

### Fixed

-   Fixed an issue where non-sha256 hashes were not checked. ([#4529](https://github.com/python-poetry/poetry/pull/4529))

## [1.1.9] - 2021-09-18

### Fixed

-   Fixed a security issue where file hashes were not checked prior to installation. ([#4420](https://github.com/python-poetry/poetry/pull/4420), [#4444](https://github.com/python-poetry/poetry/pull/4444), [python-poetry/poetry-core#193](https://github.com/python-poetry/poetry-core/pull/193))
-   Fixed the detection of the system environment when the setting `virtualenvs.create` is deactivated. ([#4507](https://github.com/python-poetry/poetry/pull/4507))
-   Fixed an issue where unsafe parameters could be passed to `git` commands. ([python-poetry/poetry-core#203](https://github.com/python-poetry/poetry-core/pull/203))
-   Fixed an issue where the wrong `git` executable could be used on Windows. ([python-poetry/poetry-core#205](https://github.com/python-poetry/poetry-core/pull/205))
## [1.1.8] - 2021-08-19

### Fixed

-   Fixed an error with repository prioritization when specifying secondary repositories. ([#4241](https://github.com/python-poetry/poetry/pull/4241))
-   Fixed the detection of the system environment when the setting `virtualenvs.create` is deactivated. ([#4330](https://github.com/python-poetry/poetry/pull/4330), [#4407](https://github.com/python-poetry/poetry/pull/4407))
-   Fixed the evaluation of relative path dependencies. ([#4246](https://github.com/python-poetry/poetry/pull/4246))
-   Fixed environment detection for Python 3.10 environments. ([#4387](https://github.com/python-poetry/poetry/pull/4387))
-   Fixed an error in the evaluation of `in/not in` markers ([python-poetry/poetry-core#189](https://github.com/python-poetry/poetry-core/pull/189))

## [1.2.0a2] - 2021-08-01

### Added

- Poetry now supports dependency groups. ([#4260](https://github.com/python-poetry/poetry/pull/4260))
- The `install` command now supports a `--sync` option to synchronize the environment with the lock file. ([#4336](https://github.com/python-poetry/poetry/pull/4336))

### Changed

- Improved the way credentials are retrieved to better support keyring backends. ([#4086](https://github.com/python-poetry/poetry/pull/4086))
- The `--remove-untracked` option of the `install` command is now deprecated in favor of the new `--sync` option. ([#4336](https://github.com/python-poetry/poetry/pull/4336))
- The user experience when installing dependency groups has been improved. ([#4336](https://github.com/python-poetry/poetry/pull/4336))

### Fixed

- Fixed performance issues when resolving dependencies. ([#3839](https://github.com/python-poetry/poetry/pull/3839))
- Fixed an issue where transitive dependencies of directory or VCS dependencies were not installed or otherwise removed. ([#4202](https://github.com/python-poetry/poetry/pull/4202))
- Fixed the behavior of the `init` command in non-interactive mode. ([#2899](https://github.com/python-poetry/poetry/pull/2899))
- Fixed the detection of the system environment when the setting `virtualenvs.create` is deactivated. ([#4329](https://github.com/python-poetry/poetry/pull/4329))
- Fixed the display of possible solutions for some common errors. ([#4332](https://github.com/python-poetry/poetry/pull/4332))


## [1.1.7] - 2021-06-25

Note: Lock files might need to be regenerated for the first fix below to take effect.\
You can use `poetry lock` to do so without the `--no-update` option.

### Changed

-   This release is compatible with the `install-poetry.py` installation script to ease the migration path from `1.1` releases to `1.2` releases. ([#4192](https://github.com/python-poetry/poetry/pull/4192))

### Fixed

-   Fixed an issue where transitive dependencies of directory or VCS dependencies were not installed or otherwise removed. ([#4203](https://github.com/python-poetry/poetry/pull/4203))
-   Fixed an issue where the combination of the `--tree` and `--no-dev` options for the show command was still displaying development dependencies. ([#3992](https://github.com/python-poetry/poetry/pull/3992))

## [1.2.0a1] - 2021-05-21

This release is the first testing release of the upcoming 1.2.0 version.

It **drops** support for Python 2.7 and 3.5.

### Added

- Poetry now supports a plugin system to alter or expand Poetry's functionality. ([#3733](https://github.com/python-poetry/poetry/pull/3733))
- Poetry now supports [PEP 610](https://www.python.org/dev/peps/pep-0610/). ([#3876](https://github.com/python-poetry/poetry/pull/3876))
- Several configuration options to better control the way virtual environments are created are now available. ([#3157](https://github.com/python-poetry/poetry/pull/3157), [#3711](https://github.com/python-poetry/poetry/pull/3711)).
- The `new` command now supports namespace packages. ([#2768](https://github.com/python-poetry/poetry/pull/2768))
- The `add` command now supports the `--editable` option to add packages in editable mode. ([#3940](https://github.com/python-poetry/poetry/pull/3940))

### Changed

- Python 2.7 and 3.5 are no longer supported. ([#3405](https://github.com/python-poetry/poetry/pull/3405))
- The usage of the `get-poetry.py` script is now deprecated and is replaced by the `install-poetry.py` script. ([#3706](https://github.com/python-poetry/poetry/pull/3706))
- Directory dependencies are now in non-develop mode by default. ([poetry-core#98](https://github.com/python-poetry/poetry-core/pull/98))
- Improved support for PEP 440 specific versions that do not abide by semantic versioning. ([poetry-core#140](https://github.com/python-poetry/poetry-core/pull/140))
- Improved the CLI experience and performance by migrating to the latest version of Cleo. ([#3618](https://github.com/python-poetry/poetry/pull/3618))
- Packages previously considered as unsafe (`pip`, `setuptools`, `wheels` and `distribute`) can now be managed as any other package. ([#2826](https://github.com/python-poetry/poetry/pull/2826))
- The `new` command now defaults to the Markdown format for README files. ([#2768](https://github.com/python-poetry/poetry/pull/2768))

### Fixed

- Fixed an error where command line options were not taken into account when using the `run` command. ([#3618](https://github.com/python-poetry/poetry/pull/3618))
- Fixed an error in the way custom repositories were resolved. ([#3406](https://github.com/python-poetry/poetry/pull/3406))

## [1.1.6] - 2021-04-14

### Fixed
-   Fixed export format for path dependencies. ([#3121](https://github.com/python-poetry/poetry/pull/3121))
-   Fixed errors caused by environment modification when executing some commands. ([#3253](https://github.com/python-poetry/poetry/pull/3253))
-   Fixed handling of wheel files with single-digit versions. ([#3338](https://github.com/python-poetry/poetry/pull/3338))
-   Fixed an error when handling single-digit Python markers. ([poetry-core#156](https://github.com/python-poetry/poetry-core/pull/156))
-   Fixed dependency markers not being properly copied when changing the constraint leading to resolution errors. ([poetry-core#163](https://github.com/python-poetry/poetry-core/pull/163))
-   Fixed an error where VCS dependencies were always updated. ([#3947](https://github.com/python-poetry/poetry/pull/3947))
-   Fixed an error where the incorrect version of a package was locked when using environment markers. ([#3945](https://github.com/python-poetry/poetry/pull/3945))

## [1.1.5] - 2021-03-04

### Fixed
- Fixed an error in the export command when no lock file existed and a verbose flag was passed to the command. (#3310)
- Fixed an error where the pyproject.toml was not reverted when using the add command. (#3622)
- Fixed errors when using non-HTTPS indices. (#3622)
- Fixed errors when handling simple indices redirection. (#3622)
- Fixed errors when trying to handle newer wheels by using the latest version of poetry-core and packaging. (#3677)
- Fixed an error when using some versions of poetry-core due to an incorrect import. (#3696)

## [1.1.4] - 2020-10-23

### Added

- Added `installer.parallel` boolean flag (defaults to `true`) configuration to enable/disable parallel execution of operations when using the new installer. ([#3088](https://github.com/python-poetry/poetry/pull/3088))

### Changed

- When using system environments as an unprivileged user, user site and bin directories are created if they do not already exist. ([#3107](https://github.com/python-poetry/poetry/pull/3107))

### Fixed

- Fixed editable installation of poetry projects when using system environments. ([#3107](https://github.com/python-poetry/poetry/pull/3107))
- Fixed locking of nested extra activations. If you were affected by this issue, you will need to regenerate the lock file using `poetry lock --no-update`.  ([#3229](https://github.com/python-poetry/poetry/pull/3229))
- Fixed prioritisation of non-default custom package sources. ([#3251](https://github.com/python-poetry/poetry/pull/3251))
- Fixed detection of installed editable packages when non-poetry managed `.pth` file exists. ([#3210](https://github.com/python-poetry/poetry/pull/3210))
- Fixed scripts generated by editable builder to use valid import statements. ([#3214](https://github.com/python-poetry/poetry/pull/3214))
- Fixed recursion error when locked dependencies contain cyclic dependencies. ([#3237](https://github.com/python-poetry/poetry/pull/3237))
- Fixed propagation of editable flag for VCS dependencies. ([#3264](https://github.com/python-poetry/poetry/pull/3264))

## [1.1.3] - 2020-10-14

### Changed

- Python version support deprecation warning is now written to `stderr`. ([#3131](https://github.com/python-poetry/poetry/pull/3131))

### Fixed

- Fixed `KeyError` when `PATH` is not defined in environment variables. ([#3159](https://github.com/python-poetry/poetry/pull/3159))
- Fixed error when using `config` command in a directory with an existing `pyproject.toml` without any Poetry configuration. ([#3172](https://github.com/python-poetry/poetry/pull/3172))
- Fixed incorrect inspection of package requirements when same dependency is specified multiple times with unique markers. ([#3147](https://github.com/python-poetry/poetry/pull/3147))
- Fixed `show` command to use already resolved package metadata. ([#3117](https://github.com/python-poetry/poetry/pull/3117))
- Fixed multiple issues with `export` command output when using `requirements.txt` format. ([#3119](https://github.com/python-poetry/poetry/pull/3119))

## [1.1.2] - 2020-10-06

### Changed
- Dependency installation of editable packages and all uninstall operations are now performed serially within their corresponding priority groups. ([#3099](https://github.com/python-poetry/poetry/pull/3099))
- Improved package metadata inspection of nested poetry projects within project path dependencies. ([#3105](https://github.com/python-poetry/poetry/pull/3105))

### Fixed

- Fixed export of `requirements.txt` when project dependency contains git dependencies. ([#3100](https://github.com/python-poetry/poetry/pull/3100))

## [1.1.1] - 2020-10-05

### Added

- Added `--no-update` option to `lock` command. ([#3034](https://github.com/python-poetry/poetry/pull/3034))

### Fixed

- Fixed resolution of packages with missing required extras. ([#3035](https://github.com/python-poetry/poetry/pull/3035))
- Fixed export of `requirements.txt` dependencies to include development dependencies. ([#3024](https://github.com/python-poetry/poetry/pull/3024))
- Fixed incorrect selection of unsupported binary distribution formats when selecting a package artifact to install. ([#3058](https://github.com/python-poetry/poetry/pull/3058))
- Fixed incorrect use of system executable when building package distributions via `build` command. ([#3056](https://github.com/python-poetry/poetry/pull/3056))
- Fixed errors in `init` command  when specifying `--dependency` in non-interactive mode when a `pyproject.toml` file already exists. ([#3076](https://github.com/python-poetry/poetry/pull/3076))
- Fixed incorrect selection of configured source url when a publish repository url configuration with the same name already exists. ([#3047](https://github.com/python-poetry/poetry/pull/3047))
- Fixed dependency resolution issues when the same package is specified in multiple dependency extras. ([#3046](https://github.com/python-poetry/poetry/pull/3046))

## [1.1.0] - 2020-10-01

### Changed

- The `init` command will now use existing `pyproject.toml` if possible ([#2448](https://github.com/python-poetry/poetry/pull/2448)).
- Error messages when metadata information retrieval fails have been improved  ([#2997](https://github.com/python-poetry/poetry/pull/2997)).

### Fixed

- Fixed parsing of version constraint for `rc` prereleases ([#2978](https://github.com/python-poetry/poetry/pull/2978)).
- Fixed how some metadata information are extracted from `setup.cfg` files ([#2957](https://github.com/python-poetry/poetry/pull/2957)).
- Fixed return codes returned by the executor ([#2981](https://github.com/python-poetry/poetry/pull/2981)).
- Fixed whitespaces not being accepted for the list of extras when adding packages ([#2985](https://github.com/python-poetry/poetry/pull/2985)).
- Fixed repositories specified in the `pyproject.toml` file not being taken into account for authentication when downloading packages ([#2990](https://github.com/python-poetry/poetry/pull/2990)).
- Fixed permission errors when installing the root project if the `site-packages` directory is not writeable ([#3002](https://github.com/python-poetry/poetry/pull/3002)).
- Fixed environment marker propagation when exporting to the `requirements.txt` format  ([#3002](https://github.com/python-poetry/poetry/pull/3002)).
- Fixed errors when paths in run command contained spaces ([#3015](https://github.com/python-poetry/poetry/pull/3015)).


## [1.1.0rc1] - 2020-09-25

### Changed

- The `virtualenvs.in-project` setting will now always be honored, if set explicitly, regardless of the presence of a `.venv` directory ([#2771](https://github.com/python-poetry/poetry/pull/2771)).
- Adding packages already present in the `pyproject.toml` file will no longer raise an error ([#2886](https://github.com/python-poetry/poetry/pull/2886)).
- Errors when authenticating against custom repositories will now be logged ([#2577](https://github.com/python-poetry/poetry/pull/2577)).

### Fixed

- Fixed an error on Python 3.5 when resolving URL dependencies ([#2954](https://github.com/python-poetry/poetry/pull/2954)).
- Fixed the `dependency` option of the `init` command being ignored ([#2587](https://github.com/python-poetry/poetry/pull/2587)).
- Fixed the `show` command displaying erroneous information following the changes in the lock file format ([#2967](https://github.com/python-poetry/poetry/pull/2967)).
- Fixed dependency resolution errors due to invalid python constraints propagation ([#2968](https://github.com/python-poetry/poetry/pull/2968)).


## [1.1.0b4] - 2020-09-23

### Changed

- When running under Python 2.7 on Windows, install command will be limited to one worker to mitigate threading issue ([#2941](https://github.com/python-poetry/poetry/pull/2941)).


## [1.1.0b3] - 2020-09-18

### Changed

- Improved the error reporting when HTTP error are encountered for legacy repositories ([#2459](https://github.com/python-poetry/poetry/pull/2459)).
- When displaying the name of packages retrieved from remote repositories, the original name will now be used ([#2305](https://github.com/python-poetry/poetry/pull/2305)).
- Failed package downloads will now be retried on connection errors ([#2813](https://github.com/python-poetry/poetry/pull/2813)).
- Path dependencies will now be installed as editable only when `develop` option is set to `true` ([#2887](https://github.com/python-poetry/poetry/pull/2887)).

### Fixed

- Fixed the detection of the type of installed packages ([#2722](https://github.com/python-poetry/poetry/pull/2722)).
- Fixed deadlocks when installing packages on systems not supporting non-ascii characters ([#2721](https://github.com/python-poetry/poetry/pull/2721)).
- Fixed handling of wildcard constraints for packages with prereleases only ([#2821](https://github.com/python-poetry/poetry/pull/2821)).
- Fixed dependencies of some packages not being discovered by ensuring we use the PEP-516 backend if specified  ([#2810](https://github.com/python-poetry/poetry/pull/2810)).
- Fixed recursion errors when retrieving extras ([#2787](https://github.com/python-poetry/poetry/pull/2787)).
- Fixed `PyPI` always being displayed when publishing even for custom repositories ([#2905](https://github.com/python-poetry/poetry/pull/2905)).
- Fixed handling of packages extras when resolving dependencies ([#2887](https://github.com/python-poetry/poetry/pull/2887)).


## [1.1.0b2] - 2020-07-24

### Changed

- Added support for build scripts without the `setup.py` file generation in the editable builder ([#2718](https://github.com/python-poetry/poetry/pull/2718)).

### Fixed

- Fixed an error occurring when using older lock files ([#2717](https://github.com/python-poetry/poetry/pull/2717)).


## [1.1.0b1] - 2020-07-24

### Changed

- Virtual environments will now exclusively be built with `virtualenv` ([#2666](https://github.com/python-poetry/poetry/pull/2666)).
- Support for Python 2.7 and 3.5 is now officially deprecated and a warning message will be displayed ([#2683](https://github.com/python-poetry/poetry/pull/2683)).
- Improved metadata inspection of packages by using the PEP-517 build system ([#2632](https://github.com/python-poetry/poetry/pull/2632)).

### Fixed

- Fixed parallel tasks not being cancelled when the installation is interrupted or has failed ([#2656](https://github.com/python-poetry/poetry/pull/2656)).
- Fixed an error where the editable builder would not expose all packages ([#2664](https://github.com/python-poetry/poetry/pull/2656)).
- Fixed an error for Python 2.7 when a file could not be downloaded in the installer ([#2709](https://github.com/python-poetry/poetry/pull/2709)).
- Fixed the lock file `content-hash` value not being updated when using the `add` and `remove` commands ([#2710](https://github.com/python-poetry/poetry/pull/2710)).
- Fixed incorrect resolution errors being raised for packages with python requirements ([#2712](https://github.com/python-poetry/poetry/pull/2712)).
- Fixed an error causing the build log messages to no longer be displayed ([#2715](https://github.com/python-poetry/poetry/pull/2715)).


## [1.0.10] - 2020-07-21

### Changed

- The lock files are now versioned to ease transitions for lock file format changes, with warnings being displayed on incompatibility detection ([#2695](https://github.com/python-poetry/poetry/pull/2695)).
- The `init` and `new` commands will now provide hints on invalid given licenses ([#1634](https://github.com/python-poetry/poetry/pull/1634)).

### Fixed

- Fixed error messages when the authors specified in the `pyproject.toml` file are invalid ([#2525](https://github.com/python-poetry/poetry/pull/2525)).
- Fixed empty `.venv` directories being deleted ([#2064](https://github.com/python-poetry/poetry/pull/2064)).
- Fixed the `shell` command for `tcsh` shells ([#2583](https://github.com/python-poetry/poetry/pull/2583)).
- Fixed errors when installing directory or file dependencies in some cases ([#2582](https://github.com/python-poetry/poetry/pull/2582)).


## [1.1.0a3] - 2020-07-10

### Added

- New installer which provides a faster and better experience ([#2595](https://github.com/python-poetry/poetry/pull/2595)).

### Fixed

- Fixed resolution error when handling duplicate dependencies with environment markers ([#2622](https://github.com/python-poetry/poetry/pull/2622)).
- Fixed erroneous resolution errors when resolving packages to install ([#2625](https://github.com/python-poetry/poetry/pull/2625)).
- Fixed errors when detecting installed editable packages ([#2602](https://github.com/python-poetry/poetry/pull/2602)).


## [1.1.0a2] - 2020-06-26

Note that lock files generated with this release are not compatible with previous releases of Poetry.

### Added

- The `install` command now supports a `--remove-untracked` option to ensure only packages from the lock file are present in the environment ([#2172](https://github.com/python-poetry/poetry/pull/2172)).
- Some errors will now be provided with possible solutions and links to the documentation ([#2396](https://github.com/python-poetry/poetry/pull/2396)).

### Changed

- Editable installations of Poetry projects have been improved and are now faster ([#2360](https://github.com/python-poetry/poetry/pull/2360)).
- Improved the accuracy of the dependency resolver in case of dependencies with environment markers ([#2361](https://github.com/python-poetry/poetry/pull/2361))
- Environment markers of dependencies are no longer stored in the lock file ([#2361](https://github.com/python-poetry/poetry/pull/2361)).
- Improved the way connection errors are handled when publishing ([#2285](https://github.com/python-poetry/poetry/pull/2285)).

### Fixed

- Fixed errors when handling duplicate dependencies with environment markers ([#2342](https://github.com/python-poetry/poetry/pull/2342)).
- Fixed the detection of installed packages ([#2360](https://github.com/python-poetry/poetry/pull/2360)).


## [1.1.0a1] - 2020-03-27

This release **must** be downloaded via the `get-poetry.py` script and not via the `self update` command.

### Added

- Added a new `--dry-run` option to the `publish` command ([#2199](https://github.com/python-poetry/poetry/pull/2199)).

### Changed

- The core features of Poetry have been extracted in to a separate library: `poetry-core` ([#2212](https://github.com/python-poetry/poetry/pull/2212)).
- The build backend is no longer `poetry.masonry.api` but `poetry.core.masonry.api` which requires `poetry-core>=1.0.0a5` ([#2212](https://github.com/python-poetry/poetry/pull/2212)).
- The exceptions are now beautifully displayed in the terminal with various level of details depending on the verbosity ([2230](https://github.com/python-poetry/poetry/pull/2230)).


## [1.0.9] - 2020-06-09

### Fixed

- Fixed an issue where packages from custom indices where continuously updated ([#2525](https://github.com/python-poetry/poetry/pull/2525)).
- Fixed errors in the way Python environment markers were parsed and generated ([#2526](https://github.com/python-poetry/poetry/pull/2526)).


## [1.0.8] - 2020-06-05

### Fixed

- Fixed a possible error when installing the root package ([#2505](https://github.com/python-poetry/poetry/pull/2505)).
- Fixed an error where directory and VCS dependencies were not installed ([#2505](https://github.com/python-poetry/poetry/pull/2505)).


## [1.0.7] - 2020-06-05

### Fixed

- Fixed an error when trying to execute some packages `setup.py` file ([#2349](https://github.com/python-poetry/poetry/pull/2349)).


## [1.0.6] - 2020-06-05

### Changed

- The `self update` command has been updated in order to handle future releases of Poetry ([#2429](https://github.com/python-poetry/poetry/pull/2429)).

### Fixed

- Fixed an error were a new line was not written when displaying the virtual environment's path with `env info` ([#2196](https://github.com/python-poetry/poetry/pull/2196)).
- Fixed a misleading error message when the `packages` property was empty ([#2265](https://github.com/python-poetry/poetry/pull/2265)).
- Fixed shell detection by using environment variables ([#2147](https://github.com/python-poetry/poetry/pull/2147)).
- Fixed the removal of VCS dependencies ([#2239](https://github.com/python-poetry/poetry/pull/2239)).
- Fixed generated wheel ABI tags for Python 3.8 ([#2121](https://github.com/python-poetry/poetry/pull/2121)).
- Fixed a regression when building stub-only packages ([#2000](https://github.com/python-poetry/poetry/pull/2000)).
- Fixed errors when parsing PEP-440 constraints with whitespace ([#2347](https://github.com/python-poetry/poetry/pull/2347)).
- Fixed PEP 508 representation of VCS dependencies ([#2349](https://github.com/python-poetry/poetry/pull/2349)).
- Fixed errors when source distributions were read-only ([#1140](https://github.com/python-poetry/poetry/pull/1140)).
- Fixed dependency resolution errors and inconsistencies with directory, file and VCS dependencies ([#2398](https://github.com/python-poetry/poetry/pull/2398)).
- Fixed custom repositories information not being properly locked ([#2484](https://github.com/python-poetry/poetry/pull/2484)).


## [1.0.5] - 2020-02-29

### Fixed

- Fixed an error when building distributions if the `git` executable was not found ([#2105](https://github.com/python-poetry/poetry/pull/2105)).
- Fixed various errors when reading Poetry's TOML files by upgrading [tomlkit](https://github.com/sdispater/tomlkit).


## [1.0.4] - 2020-02-28

### Fixed

- Fixed the PyPI URL used when installing packages ([#2099](https://github.com/python-poetry/poetry/pull/2099)).
- Fixed errors when the author's name contains special characters ([#2006](https://github.com/python-poetry/poetry/pull/2006)).
- Fixed VCS excluded files detection when building wheels ([#1947](https://github.com/python-poetry/poetry/pull/1947)).
- Fixed packages detection when building sdists ([#1626](https://github.com/python-poetry/poetry/pull/1626)).
- Fixed the local `.venv` virtual environment not being displayed in `env list` ([#1762](https://github.com/python-poetry/poetry/pull/1762)).
- Fixed incompatibilities with the most recent versions of `virtualenv` ([#2096](https://github.com/python-poetry/poetry/pull/2096)).
- Fixed Poetry's own vendor dependencies being retrieved when updating dependencies ([#1981](https://github.com/python-poetry/poetry/pull/1981)).
- Fixed encoding of credentials in URLs ([#1911](https://github.com/python-poetry/poetry/pull/1911)).
- Fixed url constraints not being accepted in multi-constraints dependencies ([#2035](https://github.com/python-poetry/poetry/pull/2035)).
- Fixed an error where credentials specified via environment variables were not retrieved ([#2061](https://github.com/python-poetry/poetry/pull/2061)).
- Fixed an error where git dependencies referencing tags were not locked to the corresponding commit ([#1948](https://github.com/python-poetry/poetry/pull/1948)).
- Fixed an error when parsing packages `setup.py` files ([#2041](https://github.com/python-poetry/poetry/pull/2041)).
- Fixed an error when parsing some git URLs ([#2018](https://github.com/python-poetry/poetry/pull/2018)).


## [1.0.3] - 2020-01-31

### Fixed

- Fixed an error which caused the configuration environment variables (like `POETRY_HTTP_BASIC_XXX_PASSWORD`) to not be used ([#1909](https://github.com/python-poetry/poetry/pull/1909)).
- Fixed an error where the `--help` option was not working ([#1910](https://github.com/python-poetry/poetry/pull/1910)).
- Fixed an error where packages from private indices were not decompressed properly ([#1851](https://github.com/python-poetry/poetry/pull/1851)).
- Fixed an error where the version of some PEP-508-formatted wheel dependencies was not properly retrieved ([#1932](https://github.com/python-poetry/poetry/pull/1932)).
- Fixed internal regexps to avoid potential catastrophic backtracking errors ([#1913](https://github.com/python-poetry/poetry/pull/1913)).
- Fixed performance issues when custom indices were defined in the `pyproject.toml` file ([#1892](https://github.com/python-poetry/poetry/pull/1892)).
- Fixed the `get_requires_for_build_wheel()` function of `masonry.api` which wasn't returning the proper result ([#1875](https://github.com/python-poetry/poetry/pull/1875)).


## [1.0.2] - 2020-01-10

### Fixed

- Reverted a previous fix ([#1796](https://github.com/python-poetry/poetry/pull/1796)) which was causing errors for projects with file and/or directory dependencies ([#1865](https://github.com/python-poetry/poetry/pull/1865)).


## [1.0.1] - 2020-01-10

### Fixed

- Fixed an error in `env use` where the wrong Python executable was being used to check compatibility ([#1736](https://github.com/python-poetry/poetry/pull/1736)).
- Fixed an error where VCS dependencies were not properly categorized as development dependencies ([#1725](https://github.com/python-poetry/poetry/pull/1725)).
- Fixed an error where some shells would no longer be usable after using the `shell` command ([#1673](https://github.com/python-poetry/poetry/pull/1673)).
- Fixed an error where explicitly included files where not included in wheel distributions ([#1750](https://github.com/python-poetry/poetry/pull/1750)).
- Fixed an error where some Git dependencies url were not properly parsed ([#1756](https://github.com/python-poetry/poetry/pull/1756)).
- Fixed an error in the `env` commands on Windows if the path to the executable contained a space ([#1774](https://github.com/python-poetry/poetry/pull/1774)).
- Fixed several errors and UX issues caused by `keyring` on some systems ([#1788](https://github.com/python-poetry/poetry/pull/1788)).
- Fixed errors when trying to detect installed packages ([#1786](https://github.com/python-poetry/poetry/pull/1786)).
- Fixed an error when packaging projects where Python packages were not properly detected ([#1592](https://github.com/python-poetry/poetry/pull/1592)).
- Fixed an error where local file dependencies were exported as editable when using the `export` command ([#1840](https://github.com/python-poetry/poetry/pull/1840)).
- Fixed the way environment markers are propagated and evaluated when resolving dependencies ([#1829](https://github.com/python-poetry/poetry/pull/1829), [#1789](https://github.com/python-poetry/poetry/pull/1789)).
- Fixed an error in the PEP-508 compliant representation of directory and file dependencies ([#1796](https://github.com/python-poetry/poetry/pull/1796)).
- Fixed an error where invalid virtual environments would be silently used. They will not be recreated and a warning will be displayed ([#1797](https://github.com/python-poetry/poetry/pull/1797)).
- Fixed an error where dependencies were not properly detected when reading the `setup.py` file in some cases ([#1764](https://github.com/python-poetry/poetry/pull/1764)).


## [1.0.0] - 2019-12-12

### Added

- Added an `export` command to export the lock file to other formats (only `requirements.txt` is currently supported).
- Added a `env info` command to get basic information about the current environment.
- Added a `env use` command to control the Python version used by the project.
- Added a `env list` command to list the virtualenvs associated with the current project.
- Added a `env remove` command to delete virtualenvs associated with the current project.
- Added support for `POETRY_HOME` declaration within `get-poetry.py`.
- Added support for declaring a specific source for dependencies.
- Added support for disabling PyPI and making another repository the default one.
- Added support for declaring private repositories as secondary.
- Added the ability to specify packages on a per-format basis.
- Added support for custom urls in metadata.
- Full environment markers are now supported for dependencies via the `markers` property.
- Added the ability to specify git dependencies directly in `add`, it no longer requires the `--git` option.
- Added the ability to specify path dependencies directly in `add`, it no longer requires the `--path` option.
- Added support for url dependencies ([#1260](https://github.com/python-poetry/poetry/pull/1260)).
- Publishing to PyPI using [API tokens](https://pypi.org/help/#apitoken) is now supported ([#1275](https://github.com/python-poetry/poetry/pull/1275)).
- Licenses can now be identified by their full name.
- Added support for custom certificate authority and client certificates for private repositories.
- Poetry can now detect and use Conda environments.

### Changed

- Slightly changed the lock file, making it potentially incompatible with previous Poetry versions.
- The `cache:clear` command has been renamed to `cache clear`.
- The `debug:info` command has been renamed to `debug info`.
- The `debug:resolve` command has been renamed to `debug resolve`.
- The `self:update` command has been renamed to `self update`.
- Changed the way virtualenvs are stored (names now depend on the project's path).
- The `--git` option of the `add` command has been removed.
- The `--path` option of the `add` command has been removed.
- The `add` command will now automatically select the latest prerelease if only prereleases are available.
- The `add` command can now update a dependencies if an explicit constraint is given ([#1221](https://github.com/python-poetry/poetry/pull/1221)).
- Removed the `--develop` option from the `install` command.
- Improved UX when searching for packages in the `init` command.
- The `shell` command has been improved.
- The `poetry run` command now uses `os.execvp()` rather than spawning a new subprocess.
- Specifying dependencies with `allows-prereleases` in the `pyproject.toml` file is deprecated for consistency with the `add` command. Use `allow-prereleases` instead.
- Improved the error message when the lock file is invalid.
- Whenever Poetry needs to use the "system" Python, it will now call `sys.executable` instead of the `python` command.
- Improved the error message displayed on conflicting Python requirements ([#1681](https://github.com/python-poetry/poetry/pull/1681)).
- Improved the `site-packages` directory detection ([#1683](https://github.com/python-poetry/poetry/pull/1683)).

### Fixed

- Fixed transitive extra dependencies being removed when updating a specific dependency.
- The `pyproject.toml` configuration is now properly validated.
- Fixed installing Poetry-based packages breaking with `pip`.
- Fixed packages with empty markers being added to the lock file.
- Fixed invalid lock file generation in some cases.
- Fixed local version identifier handling in wheel file names.
- Fixed packages with invalid metadata triggering an error instead of being skipped.
- Fixed the generation of invalid lock files in some cases.
- Git dependencies are now properly locked to a specific revision when specifying a branch or a tag.
- Fixed the behavior of the `~=` operator.
- Fixed dependency resolution for conditional development dependencies.
- Fixed generated dependency constraints when they contain inequality operators.
- The `run` command now properly handles the `--` separator.
- Fixed some issues with `path` dependencies being seen as `git` dependencies.
- Fixed various issues with the way `extra` markers in dependencies were handled.
- Fixed the option conflicts in the `run` command.
- Fixed wrong latest version being displayed when executing `show -l`.
- Fixed `TooManyRedirects` errors being raised when resolving dependencies.
- Fixed custom indices dependencies being constantly updated.
- Fixed the behavior of the `--install` option of the debug resolve command.
- Fixed an error in `show` when using the `-o/--outdated` option.
- Fixed PEP 508 url dependency handling.
- Fixed excluded files via the `exclude` being included in distributions.
- Fixed  an error in `env use` if the `virtualenvs.in-project` setting is activated ([#1682](https://github.com/python-poetry/poetry/pull/1682))
- Fixed handling of `empty` and `any` markers in unions of markers ([#1650](https://github.com/python-poetry/poetry/pull/1650)).


## [0.12.17] - 2019-07-03

### Fixed

- Fixed dependency resolution with circular dependencies.
- Fixed encoding errors when reading files on Windows. (Thanks to [@vlcinsky](https://github.com/vlcinsky))
- Fixed unclear errors when executing commands in virtual environments. (Thanks to [@Imaclean74](https://github.com/Imaclean74))
- Fixed handling of `.venv` when it's not a directory. (Thanks to [@mpanarin](https://github.com/mpanarin))


## [0.12.16] - 2019-05-17

### Fixed

- Fixed packages with no hashes retrieval for legacy repositories.
- Fixed multiple constraints for dev dependencies.
- Fixed dependency resolution failing on badly formed package versions instead of skipping.
- Fixed permissions of built wheels.


## [0.12.15] - 2019-05-03

### Fixed

- Fixed an `AttributeError` in the editable builder.
- Fixed resolution of packages with only Python 3 wheels and sdist when resolving for legacy repositories.
- Fixed non-sha256 hashes retrieval for legacy repositories.


## [0.12.14] - 2019-04-26

### Fixed

- Fixed root package installation for pure Python packages.


## [0.12.13] - 2019-04-26

### Fixed

- Fixed root package installation with `pip>=19.0`.
- Fixed packages not being removed after using the `remove` command.


## [0.12.12] - 2019-04-11

### Fixed

- Fix lock idempotency.
- Fix markers evaluation for `python_version` with precision < 3.
- Fix permissions of the `dist-info` files.
- Fix `prepare_metadata_for_build_wheel()` missing in the build backend.
- Fix metadata inconsistency between wheels and sdists.
- Fix parsing of `platform_release` markers.
- Fix metadata information when the project has git dependencies.
- Fix error reporting when publishing fails.
- Fix retrieval of `extras_require` in some `setup.py` files. (Thanks to [@asodeur](https://github.com/asodeur))
- Fix wheel compression when building. (Thanks to [@ccosby](https://github.com/ccosby))
- Improve retrieval of information for packages with two python specific wheels.
- Fix request authentication when credentials are included in URLs. (Thanks to [@connorbrinton](https://github.com/connorbrinton))


## [0.12.11] - 2019-01-13

### Fixed

- Fixed the way packages information are retrieved for legacy repositories.
- Fixed an error when adding packages with invalid versions.
- Fixed an error when resolving directory dependencies with no sub dependencies.
- Fixed an error when locking packages with no description.
- Fixed path resolution for transitive file dependencies.
- Fixed multiple constraints handling for the root package.
- Fixed exclude functionality on case sensitive systems.


## [0.12.10] - 2018-11-22

### Fixed

- Fixed `run` not executing scripts.
- Fixed environment detection.
- Fixed handling of authentication for legacy repositories.


## [0.12.9] - 2018-11-19

### Fixed

- Fixed executables from outside the virtualenv not being accessible.
- Fixed a possible error when building distributions with the `exclude` option.
- Fixed the `run` command for namespaced packages.
- Fixed errors for virtualenvs with spaces in their path.
- Fixed prerelease versions being selected with the `add` command.


## [0.12.8] - 2018-11-13

### Fixed

- Fixed permission errors when adding/removing git dependencies on Windows.
- Fixed `Pool` not raising an exception when no package could be found.
- Fixed reading `bz2` source distribution.
- Fixed handling of arbitrary equals in `InstalledRepository`.


## [0.12.7] - 2018-11-08

### Fixed

- Fixed reading of some `setup.py` files.
- Fixed a `KeyError` when getting information for packages which require reading setup files.
- Fixed the building of wheels with C extensions and an `src` layout.
- Fixed extras being selected when resolving dependencies even when not required.
- Fixed performance issues when packaging projects if a lot of files were excluded.
- Fixed installation of files.
- Fixed extras not being retrieved for legacy repositories.
- Fixed invalid transitive constraints raising an error for legacy repositories.


## [0.12.6] - 2018-11-05

### Changed

- Poetry will now try to read, without executing, setup files (`setup.py` and/or `setup.cfg`) if the `egg_info` command fails when resolving dependencies.

### Fixed

- Fixed installation of directory dependencies.
- Fixed handling of dependencies with a `not in` marker operator.
- Fixed support for VCS dependencies.
- Fixed the `exclude` property not being respected if no VCS was available.


## [0.12.5] - 2018-10-26

### Fixed

- Fixed installation of Poetry git dependencies with a build system.
- Fixed possible errors when resolving dependencies for specific packages.
- Fixed handling of Python versions compatibility.
- Fixed the dependency resolver picking up unnecessary dependencies due to not using the `python_full_version` marker.
- Fixed the `Python-Requires` metadata being invalid for single Python versions.


## [0.12.4] - 2018-10-21

### Fixed

- Fixed possible error on some combinations of markers.
- Fixed venv detection so that it only uses `VIRTUAL_ENV` to detect activated virtualenvs.


## [0.12.3] - 2018-10-18

### Fixed

- Fixed the `--no-dev` option in `install` not working properly.
- Fixed prereleases being selected even if another constraint conflicted with them.
- Fixed an error when installing current package in development mode if the generated `setup.py` had special characters.
- Fixed an error in `install` for applications not following a known structure.
- Fixed an error when trying to retrieve the current environment.
- Fixed `debug:info` not showing the current project's virtualenv.


## [0.12.2] - 2018-10-17

### Fixed

- Fixed an error when installing from private repositories.
- Fixed an error when trying to move the lock file on Python 2.7.


## [0.12.1] - 2018-10-17

### Fixed

- Fixed an error when license is unspecified.


## [0.12.0] - 2018-10-17

### Added

- Added a brand new installer.
- Added support for multi-constraints dependencies.
- Added a cache version system.
- Added a `--lock` option to `update` to only update the lock file without executing operations. (Thanks to [@greysteil](https://github.com/greysteil))
- Added support for the `Project-URL` metadata.
- Added support for optional scripts.
- Added a `--no-dev` option to `show`. (Thanks to [@rodcloutier](https://github.com/rodcloutier))

### Changed

- Improved virtualenv detection and management.
- Wildcard `python` dependencies are now equivalent to `~2.7 || ^3.4`.
- Changed behavior of the resolver for conditional dependencies.
- The `install` command will now install the current project in editable mode.
- The `develop` command is now deprecated in favor of `install`.
- Improved the `check` command.
- Empty passwords are now supported when publishing.

### Fixed

- Fixed a memory leak in the resolver.
- Fixed a recursion error on duplicate dependencies with only different extras.
- Fixed handling of extras.
- Fixed duplicate entries in both sdist and wheel.
- Fixed excluded files appearing in the `package_data` of the generated `setup.py`.
- Fixed transitive directory dependencies installation.
- Fixed file permissions for configuration and authentication files.
- Fixed an error in `cache:clear` for Python 2.7.
- Fixed publishing for the first time with a prerelease.


## [0.11.5] - 2018-09-04

### Fixed

- Fixed a recursion error with circular dependencies.
- Fixed the `config` command setting incorrect values for paths.
- Fixed an `OSError` on Python >= 3.5 for `git` dependencies with recursive symlinks.
- Fixed the possible deletion of system paths by `cache:clear`.
- Fixed a performance issue when parsing the lock file by upgrading `tomlkit`.


## [0.11.4] - 2018-07-30

### Fixed

- Fixed wrong wheel being selected when resolving dependencies.
- Fixed an error when publishing.
- Fixed an error when building wheels with the `packages` property set.
- Fixed single value display in `config` command.


## [0.11.3] - 2018-07-26

### Changed

- Poetry now only uses [TOML Kit](https://github.com/sdispater/tomlkit) for TOML files manipulation.
- Improved dependency resolution debug information.

### Fixed

- Fixed missing dependency information for some packages.
- Fixed handling of single versions when packaging.
- Fixed dependency information retrieval from `.zip` and `.bz2` archives.
- Fixed searching for and installing packages from private repositories with authentication. (Thanks to [@MarcDufresne](https://github.com/MarcDufresne))
- Fixed a potential error when checking the `pyproject.toml` validity. (Thanks to [@ojii](https://github.com/ojii))
- Fixed the lock file not tracking the `extras` information from `pyproject.toml`. (Thanks to [@cauebs](https://github.com/cauebs))
- Fixed missing trailing slash in the Simple API urls for private repositories. (Thanks to [@bradsbrown](https://github.com/bradsbrown))


## [0.11.2] - 2018-07-03

### Fixed

- Fixed missing dependencies when resolving in some cases.
- Fixed path dependencies not working in `dev-dependencies`.
- Fixed license validation in `init`. (Thanks to [@cauebs](https://github.com/cauebs))


## [0.11.1] - 2018-06-29

### Fixed

- Fixed an error when locking dependencies on Python 2.7.


## [0.11.0] - 2018-06-28

### Added

- Added support for `packages`, `include` and `exclude` properties.
- Added a new `shell` command. (Thanks to [@cauebs](https://github.com/cauebs))
- Added license validation in `init` command.

### Changed

- Changed the dependency installation order, deepest dependencies are now installed first.
- Improved solver error messages.
- `poetry` now always reads/writes the `pyproject.toml` file with the `utf-8` encoding.
- `config --list` now lists all available settings.
- `init` no longer adds `pytest` to development dependencies.

### Fixed

- Fixed handling of duplicate dependencies with different constraints.
- Fixed system requirements in lock file for sub dependencies.
- Fixed detection of new prereleases.
- Fixed unsafe packages being locked.
- Fixed versions detection in custom repositories.
- Fixed package finding with multiple custom repositories.
- Fixed handling of root incompatibilities.
- Fixed an error where packages from custom repositories would not be found.
- Fixed wildcard Python requirement being wrongly set in distributions metadata.
- Fixed installation of packages from a custom repository.
- Fixed `remove` command's case sensitivity. (Thanks to [@cauebs](https://github.com/cauebs))
- Fixed detection of `.egg-info` directory for non-poetry projects. (Thanks to [@gtors](https://github.com/gtors))
- Fixed only-wheel builds. (Thanks to [@gtors](https://github.com/gtors))
- Fixed key and array order in lock file to avoid having differences when relocking.
- Fixed errors when `git` could not be found.


## [0.10.3] - 2018-06-04

### Fixed

- Fixed `self:update` command on Windows.
- Fixed `self:update` not picking up new versions.
- Fixed a `RuntimeError` on Python 3.7.
- Fixed bad version number being picked with private repositories.
- Fixed handling of duplicate dependencies with same constraint.
- Fixed installation from custom repositories.
- Fixed setting an explicit version in `version` command.
- Fixed parsing of wildcards version constraints.


## [0.10.2] - 2018-05-31

### Fixed

- Fixed handling of `in` environment markers with commas.
- Fixed a `UnicodeDecodeError` when an error occurs in venv.
- Fixed Python requirements not properly set when resolving dependencies.
- Fixed terminal coloring being activated even if not supported.
- Fixed wrong executable being picked up on Windows in `poetry run`.
- Fixed error when listing distribution links for private repositories.
- Fixed handling of PEP 440 `~=` version constraint.


## [0.10.1] - 2018-05-28

### Fixed

- Fixed packages not found for prerelease version constraints when resolving dependencies.
- Fixed `init` and `add` commands.


## [0.10.0] - 2018-05-28

### Added

- Added a new, more efficient dependency resolver.
- Added a new `init` command to generate a `pyproject.toml` file in existing projects.
- Added a new setting `settings.virtualenvs.in-project` to make `poetry` create the project's virtualenv inside the project's directory.
- Added the `--extras` and `--python` options to `debug:resolve` to help debug dependency resolution.
- Added a `--src` option to `new` command to create an `src` layout.
- Added support for specifying the `platform` for dependencies.
- Added the `--python` option to the `add` command.
- Added the `--platform` option to the `add` command.
- Added a `--develop` option to the install command to install path dependencies in development/editable mode.
- Added a `develop` command to install the current project in development mode.

### Changed

- Improved the `show` command to make it easier to check if packages are properly installed.
- The `script` command has been deprecated, use `run` instead.
- The `publish` command no longer build packages by default. Use `--build` to retrieve the previous behavior.
- Improved support for private repositories.
- Expanded version constraints now keep the original version's precision.
- The lock file hash no longer uses the project's name and version.
- The `LICENSE` file, or similar, is now automatically added to the built packages.

### Fixed

- Fixed the dependency resolver selecting incompatible packages.
- Fixed override of dependency with dependency with extras in `dev-dependencies`.


## [0.9.1] - 2018-05-18

### Fixed

- Fixed handling of package names with dots. (Thanks to [bertjwregeer](https://github.com/bertjwregeer))
- Fixed path dependencies being resolved from the current path instead of the `pyproject.toml` file. (Thanks to [radix](https://github.com/radix))


## [0.9.0] - 2018-05-07

### Added

- Added the `cache:clear` command.
- Added support for `git` dependencies in the `add` command.
- Added support for `path` dependencies in the `add` command.
- Added support for extras in the `add` command.
- Added support for directory dependencies.
- Added support for `src/` layout for packages.
- Added automatic detection of `.venv` virtualenvs.

### Changed

- Drastically improved dependency resolution speed.
- Dependency resolution caches now use sha256 hashes.
- Changed CLI error style.
- Improved debugging of dependency resolution.
- Poetry now attempts to find `pyproject.toml` not only in the directory it was
invoked in, but in all its parents up to the root. This allows to run Poetry
commands in project subdirectories.
- Made the email address for authors optional.

### Fixed

- Fixed handling of extras when resolving dependencies.
- Fixed `self:update` command for some installation.
- Fixed handling of extras when building projects.
- Fixed handling of wildcard dependencies wen packaging/publishing.
- Fixed an error when adding a new packages with prereleases in lock file.
- Fixed packages name normalization.


## [0.8.6] - 2018-04-30

### Fixed

- Fixed config files not being created.


## [0.8.5] - 2018-04-19

### Fixed

- Fixed a bug in dependency resolution which led to installation errors.
- Fixed a bug where malformed sdists would lead to dependency resolution failing.


## [0.8.4] - 2018-04-18

### Fixed

- Fixed a bug where dependencies constraints in lock were too strict.
- Fixed unicode error in `search` command for Python 2.7.
- Fixed error with git dependencies.


## [0.8.3] - 2018-04-16

### Fixed

- Fixed platform verification which led to missing packages.
- Fixed duplicates in `pyproject.lock`.


## [0.8.2] - 2018-04-14

### Fixed

- Fixed `add` command picking up prereleases by default.
- Fixed dependendency resolution on Windows when unpacking distributions.
- Fixed dependency resolution with post releases.
- Fixed dependencies being installed even if not necessary for current system.


## [0.8.1] - 2018-04-13

### Fixed

- Fixed resolution with bad (empty) releases.
- Fixed `version` for prereleases.
- Fixed `search` not working outside of a project.
- Fixed `self:update` not working outside of a project.


## [0.8.0] - 2018-04-13

### Added

- Added support for Python 2.7.
- Added a fallback mechanism for missing dependencies.
- Added the `search` command.
- Added support for local files as dependencies.
- Added the `self:update` command.

### Changes

- Improved dependency resolution time by using cache control.

### Fixed

- Fixed `install_requires` and `extras` in generated sdist.
- Fixed dependency resolution crash with malformed dependencies.
- Fixed errors when `license` metadata is not set.
- Fixed missing information in lock file.


## [0.7.1] - 2018-04-05

### Fixed

- Fixed dependency resolution for custom repositories.


## [0.7.0] - 2018-04-04

### Added

- Added compatibility with Python 3.4 and 3.5.
- Added the `version` command to automatically bump the package's version.
- Added a standalone installer to install `poetry` isolated.
- Added support for classifiers in `pyproject.toml`.
- Added the `script` command.

### Changed

- Improved dependency resolution to avoid unnecessary operations.
- Improved dependency resolution speed.
- Improved CLI reactivity by deferring imports.
- License classifier is not automatically added to classifiers.

### Fixed

- Fixed handling of markers with the `in` operator.
- Fixed `update` not properly adding new packages to the lock file.
- Fixed solver adding uninstall operations for non-installed packages.
- Fixed `new` command creating invalid `pyproject.toml` files.


## [0.6.5] - 2018-03-22

### Fixed

- Fixed handling of extras in wheels metadata.


## [0.6.4] - 2018-03-21

### Added

- Added a `debug:info` command to get information about current environment.

### Fixed

- Fixed Python version retrieval inside virtualenvs.
- Fixed optional dependencies being set as required in sdist.
- Fixed `--optional` option in the `add` command not being used.


## [0.6.3] - 2018-03-20

### Fixed

- Fixed built wheels not getting information from the virtualenv.
- Fixed building wheel with conditional extensions.
- Fixed missing files in built wheel with extensions.
- Fixed call to venv binaries on windows.
- Fixed subdependencies representation in lock file.


## [0.6.2] - 2018-03-19

### Changed

- Changed how wildcard constraints are handled.

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



[Unreleased]: https://github.com/python-poetry/poetry/compare/1.2.0b2...master
[1.2.0b2]: https://github.com/python-poetry/poetry/compare/1.2.0b2
[1.2.0b1]: https://github.com/python-poetry/poetry/compare/1.2.0b1
[1.2.0a2]: https://github.com/python-poetry/poetry/compare/1.2.0a2
[1.2.0a1]: https://github.com/python-poetry/poetry/compare/1.2.0a1
[1.1.13]: https://github.com/python-poetry/poetry/releases/tag/1.1.13
[1.1.12]: https://github.com/python-poetry/poetry/releases/tag/1.1.12
[1.1.11]: https://github.com/python-poetry/poetry/releases/tag/1.1.11
[1.1.10]: https://github.com/python-poetry/poetry/releases/tag/1.1.10
[1.1.9]: https://github.com/python-poetry/poetry/releases/tag/1.1.9
[1.1.8]: https://github.com/python-poetry/poetry/releases/tag/1.1.8
[1.1.7]: https://github.com/python-poetry/poetry/releases/tag/1.1.7
[1.1.6]: https://github.com/python-poetry/poetry/releases/tag/1.1.6
[1.1.5]: https://github.com/python-poetry/poetry/releases/tag/1.1.5
[1.1.4]: https://github.com/python-poetry/poetry/releases/tag/1.1.4
[1.1.3]: https://github.com/python-poetry/poetry/releases/tag/1.1.3
[1.1.2]: https://github.com/python-poetry/poetry/releases/tag/1.1.2
[1.1.1]: https://github.com/python-poetry/poetry/releases/tag/1.1.1
[1.1.0]: https://github.com/python-poetry/poetry/releases/tag/1.1.0
[1.1.0rc1]: https://github.com/python-poetry/poetry/releases/tag/1.1.0rc1
[1.1.0b4]: https://github.com/python-poetry/poetry/releases/tag/1.1.0b4
[1.1.0b3]: https://github.com/python-poetry/poetry/releases/tag/1.1.0b3
[1.1.0b2]: https://github.com/python-poetry/poetry/releases/tag/1.1.0b2
[1.1.0b1]: https://github.com/python-poetry/poetry/releases/tag/1.1.0b1
[1.1.0a3]: https://github.com/python-poetry/poetry/releases/tag/1.1.0a3
[1.1.0a2]: https://github.com/python-poetry/poetry/releases/tag/1.1.0a2
[1.1.0a1]: https://github.com/python-poetry/poetry/releases/tag/1.1.0a1
[1.0.10]: https://github.com/python-poetry/poetry/releases/tag/1.0.10
[1.0.9]: https://github.com/python-poetry/poetry/releases/tag/1.0.9
[1.0.8]: https://github.com/python-poetry/poetry/releases/tag/1.0.8
[1.0.7]: https://github.com/python-poetry/poetry/releases/tag/1.0.7
[1.0.6]: https://github.com/python-poetry/poetry/releases/tag/1.0.6
[1.0.5]: https://github.com/python-poetry/poetry/releases/tag/1.0.5
[1.0.4]: https://github.com/python-poetry/poetry/releases/tag/1.0.4
[1.0.3]: https://github.com/python-poetry/poetry/releases/tag/1.0.3
[1.0.2]: https://github.com/python-poetry/poetry/releases/tag/1.0.2
[1.0.1]: https://github.com/python-poetry/poetry/releases/tag/1.0.1
[1.0.0]: https://github.com/python-poetry/poetry/releases/tag/1.0.0
[0.12.17]: https://github.com/python-poetry/poetry/releases/tag/0.12.17
[0.12.16]: https://github.com/python-poetry/poetry/releases/tag/0.12.16
[0.12.15]: https://github.com/python-poetry/poetry/releases/tag/0.12.15
[0.12.14]: https://github.com/python-poetry/poetry/releases/tag/0.12.14
[0.12.13]: https://github.com/python-poetry/poetry/releases/tag/0.12.13
[0.12.12]: https://github.com/python-poetry/poetry/releases/tag/0.12.12
[0.12.11]: https://github.com/python-poetry/poetry/releases/tag/0.12.11
[0.12.10]: https://github.com/python-poetry/poetry/releases/tag/0.12.10
[0.12.9]: https://github.com/python-poetry/poetry/releases/tag/0.12.9
[0.12.8]: https://github.com/python-poetry/poetry/releases/tag/0.12.8
[0.12.7]: https://github.com/python-poetry/poetry/releases/tag/0.12.7
[0.12.6]: https://github.com/python-poetry/poetry/releases/tag/0.12.6
[0.12.5]: https://github.com/python-poetry/poetry/releases/tag/0.12.5
[0.12.4]: https://github.com/python-poetry/poetry/releases/tag/0.12.4
[0.12.3]: https://github.com/python-poetry/poetry/releases/tag/0.12.3
[0.12.2]: https://github.com/python-poetry/poetry/releases/tag/0.12.2
[0.12.1]: https://github.com/python-poetry/poetry/releases/tag/0.12.1
[0.12.0]: https://github.com/python-poetry/poetry/releases/tag/0.12.0
[0.11.5]: https://github.com/python-poetry/poetry/releases/tag/0.11.5
[0.11.4]: https://github.com/python-poetry/poetry/releases/tag/0.11.4
[0.11.3]: https://github.com/python-poetry/poetry/releases/tag/0.11.3
[0.11.2]: https://github.com/python-poetry/poetry/releases/tag/0.11.2
[0.11.1]: https://github.com/python-poetry/poetry/releases/tag/0.11.1
[0.11.0]: https://github.com/python-poetry/poetry/releases/tag/0.11.0
[0.10.3]: https://github.com/python-poetry/poetry/releases/tag/0.10.3
[0.10.2]: https://github.com/python-poetry/poetry/releases/tag/0.10.2
[0.10.1]: https://github.com/python-poetry/poetry/releases/tag/0.10.1
[0.10.0]: https://github.com/python-poetry/poetry/releases/tag/0.10.0
[0.9.1]: https://github.com/python-poetry/poetry/releases/tag/0.9.1
[0.9.0]: https://github.com/python-poetry/poetry/releases/tag/0.9.0
[0.8.6]: https://github.com/python-poetry/poetry/releases/tag/0.8.6
[0.8.5]: https://github.com/python-poetry/poetry/releases/tag/0.8.5
[0.8.4]: https://github.com/python-poetry/poetry/releases/tag/0.8.4
[0.8.3]: https://github.com/python-poetry/poetry/releases/tag/0.8.3
[0.8.2]: https://github.com/python-poetry/poetry/releases/tag/0.8.2
[0.8.1]: https://github.com/python-poetry/poetry/releases/tag/0.8.1
[0.8.0]: https://github.com/python-poetry/poetry/releases/tag/0.8.0
[0.7.1]: https://github.com/python-poetry/poetry/releases/tag/0.7.1
[0.7.0]: https://github.com/python-poetry/poetry/releases/tag/0.7.0
[0.6.5]: https://github.com/python-poetry/poetry/releases/tag/0.6.5
[0.6.4]: https://github.com/python-poetry/poetry/releases/tag/0.6.4
[0.6.3]: https://github.com/python-poetry/poetry/releases/tag/0.6.3
[0.6.2]: https://github.com/python-poetry/poetry/releases/tag/0.6.2
[0.6.1]: https://github.com/python-poetry/poetry/releases/tag/0.6.1
[0.6.0]: https://github.com/python-poetry/poetry/releases/tag/0.6.0
[0.5.0]: https://github.com/python-poetry/poetry/releases/tag/0.5.0
[0.4.2]: https://github.com/python-poetry/poetry/releases/tag/0.4.2
[0.4.1]: https://github.com/python-poetry/poetry/releases/tag/0.4.1
[0.4.0]: https://github.com/python-poetry/poetry/releases/tag/0.4.0
[0.3.0]: https://github.com/python-poetry/poetry/releases/tag/0.3.0
[0.2.0]: https://github.com/python-poetry/poetry/releases/tag/0.2.0
[0.1.0]: https://github.com/python-poetry/poetry/releases/tag/0.1.0
