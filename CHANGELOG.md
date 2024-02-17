# Change Log


## [1.8.0] - 2024-02-25

### Added

- **Add a `non-package` mode for use cases where Poetry is only used for dependency management** ([#8650](https://github.com/python-poetry/poetry/pull/8650)).
- **Add support for PEP 658 to fetch metadata without having to download wheels** ([#5509](https://github.com/python-poetry/poetry/pull/5509)).
- **Add a `lazy-wheel` config option (default: `true`) to reduce wheel downloads during dependency resolution** ([#8815](https://github.com/python-poetry/poetry/pull/8815),
[#8941](https://github.com/python-poetry/poetry/pull/8941)).
- Improve performance of dependency resolution by using shallow copies instead of deep copies ([#8671](https://github.com/python-poetry/poetry/pull/8671)).
- `poetry check` validates that no unknown sources are referenced in dependencies ([#8709](https://github.com/python-poetry/poetry/pull/8709)).
- Add archive validation during installation for further hash algorithms ([#8851](https://github.com/python-poetry/poetry/pull/8851)).
- Add a `to` key in `tool.poetry.packages` to allow custom subpackage names ([#8791](https://github.com/python-poetry/poetry/pull/8791)).
- Add a config option to disable `keyring` ([#8910](https://github.com/python-poetry/poetry/pull/8910)).
- Add a `--sync` option to `poetry update` ([#8931](https://github.com/python-poetry/poetry/pull/8931)).
- Add an `--output` option to `poetry build` ([#8828](https://github.com/python-poetry/poetry/pull/8828)).
- Add a `--dist-dir` option to `poetry publish` ([#8828](https://github.com/python-poetry/poetry/pull/8828)).

### Changed

- **The implicit PyPI source is disabled if at least one primary source is configured** ([#8771](https://github.com/python-poetry/poetry/pull/8771)).
- **Deprecate source priority `default`** ([#8771](https://github.com/python-poetry/poetry/pull/8771)).
- **Upgrade the warning about an inconsistent lockfile to an error** ([#8737](https://github.com/python-poetry/poetry/pull/8737)).
- Deprecate setting `installer.modern-installation` to `false` ([#8988](https://github.com/python-poetry/poetry/pull/8988)).
- Drop support for `pip<19` ([#8894](https://github.com/python-poetry/poetry/pull/8894)).
- Require `requests-toolbelt>=1` ([#8680](https://github.com/python-poetry/poetry/pull/8680)).
- Allow `platformdirs` 4.x ([#8668](https://github.com/python-poetry/poetry/pull/8668)).
- Allow and require `xattr` 1.x on macOS ([#8801](https://github.com/python-poetry/poetry/pull/8801)).
- Improve venv shell activation in `fish` ([#8804](https://github.com/python-poetry/poetry/pull/8804)).
- Rename `system` to `base` in output of `poetry env info` ([#8832](https://github.com/python-poetry/poetry/pull/8832)).
- Use pretty name in output of `poetry version` ([#8849](https://github.com/python-poetry/poetry/pull/8849)).
- Improve error handling for invalid entries in `tool.poetry.scripts` ([#8898](https://github.com/python-poetry/poetry/pull/8898)).
- Improve verbose output for dependencies with extras during dependency resolution ([#8834](https://github.com/python-poetry/poetry/pull/8834)).
- Improve message about an outdated lockfile ([#8962](https://github.com/python-poetry/poetry/pull/8962)).

### Fixed

- Fix an issue where `poetry shell` failed when Python has been installed with MSYS2 ([#8644](https://github.com/python-poetry/poetry/pull/8644)).
- Fix an issue where Poetry commands failed in a terminal with a non-UTF-8 encoding ([#8608](https://github.com/python-poetry/poetry/pull/8608)).
- Fix an issue where a missing project name caused an incomprehensible error message ([#8691](https://github.com/python-poetry/poetry/pull/8691)).
- Fix an issue where Poetry failed to install an `sdist` path dependency ([#8682](https://github.com/python-poetry/poetry/pull/8682)).
- Fix an issue where `poetry install` failed because an unused extra was not available ([#8548](https://github.com/python-poetry/poetry/pull/8548)).
- Fix an issue where `poetry install --sync` did not remove an unrequested extra ([#8621](https://github.com/python-poetry/poetry/pull/8621)).
- Fix an issue where `poetry init` did not allow specific characters in the author field ([#8779](https://github.com/python-poetry/poetry/pull/8779)).
- Fix an issue where Poetry could not download `sdists` from misconfigured servers ([#8701](https://github.com/python-poetry/poetry/pull/8701)).
- Fix an issue where metadata of sdists that call CLI tools of their build requirements could not be determined ([#8827](https://github.com/python-poetry/poetry/pull/8827)).
- Fix an issue where Poetry failed to use the currently activated environment ([#8831](https://github.com/python-poetry/poetry/pull/8831)).
- Fix an issue where `poetry shell` failed in `zsh` if a space was in the venv path ([#7245](https://github.com/python-poetry/poetry/pull/7245)).
- Fix an issue where scripts with extras could not be installed ([#8900](https://github.com/python-poetry/poetry/pull/8900)).
- Fix an issue where explicit sources where not propagated correctly ([#8835](https://github.com/python-poetry/poetry/pull/8835)).
- Fix an issue where debug prints where swallowed when using a build script ([#8760](https://github.com/python-poetry/poetry/pull/8760)).
- Fix an issue where explicit sources of locked dependencies where not propagated correctly ([#8948](https://github.com/python-poetry/poetry/pull/8948)).
- Fix an issue where Poetry's own environment was falsely identified as system environment ([#8970](https://github.com/python-poetry/poetry/pull/8970)).
- Fix an issue where dependencies from a `setup.py` were ignored silently ([#9000](https://github.com/python-poetry/poetry/pull/9000)).
- Fix an issue where environment variables for `virtualenv.options` were ignored ([#9015](https://github.com/python-poetry/poetry/pull/9015)).
- Fix an issue where `virtualenvs.options.no-pip` and `virtualenvs.options.no-setuptools` were not normalized ([#9015](https://github.com/python-poetry/poetry/pull/9015)).

### Docs

- Replace deprecated `--no-dev` with `--without dev` in the FAQ ([#8659](https://github.com/python-poetry/poetry/pull/8659)).
- Recommend `poetry-check` instead of the deprecated `poetry-lock` pre-commit hook ([#8675](https://github.com/python-poetry/poetry/pull/8675)).
- Clarify the names of the environment variables to provide credentials for repositories ([#8782](https://github.com/python-poetry/poetry/pull/8782)).
- Add note how to install several version of Poetry in parallel ([#8814](https://github.com/python-poetry/poetry/pull/8814)).
- Improve description of `poetry show --why` ([#8817](https://github.com/python-poetry/poetry/pull/8817)).
- Improve documentation of `poetry update` ([#8706](https://github.com/python-poetry/poetry/pull/8706)).
- Add a warning about passing variables that may start with a hyphen via command line ([#8850](https://github.com/python-poetry/poetry/pull/8850)).
- Mention that the virtual environment in which Poetry itself is installed should not be activated ([#8833](https://github.com/python-poetry/poetry/pull/8833)).
- Add note about `poetry run` and externally managed environments ([#8748](https://github.com/python-poetry/poetry/pull/8748)).
- Update FAQ entry about `tox` for `tox` 4.x ([#8658](https://github.com/python-poetry/poetry/pull/8658)).
- Fix documentation for default `format` option for `include` and `exclude` value ([#8852](https://github.com/python-poetry/poetry/pull/8852)).
- Add note about `tox` and configured credentials ([#8888](https://github.com/python-poetry/poetry/pull/8888)).
- Add note and link how to install `pipx` ([#8878](https://github.com/python-poetry/poetry/pull/8878)).
- Fix examples for `poetry add` with git dependencies over ssh ([#8911](https://github.com/python-poetry/poetry/pull/8911)).
- Remove reference to deprecated scripts extras feature ([#8903](https://github.com/python-poetry/poetry/pull/8903)).
- Change examples to prefer `--only main` instead of `--without dev` ([#8921](https://github.com/python-poetry/poetry/pull/8921)).
- Mention that the `develop` attribute is a Poetry-specific feature and not propagated to other tools ([#8971](https://github.com/python-poetry/poetry/pull/8971)).
- Fix examples for adding supplemental and secondary sources ([#8953](https://github.com/python-poetry/poetry/pull/8953)).
- Add PyTorch example for explicit sources ([#9006](https://github.com/python-poetry/poetry/pull/9006)).

### poetry-core ([`1.9.0`](https://github.com/python-poetry/poetry-core/releases/tag/1.9.0))

- **Deprecate scripts that depend on extras** ([#690](https://github.com/python-poetry/poetry-core/pull/690)).
- Add support for path dependencies that do not define a build system ([#675](https://github.com/python-poetry/poetry-core/pull/675)).
- Update list of supported licenses ([#659](https://github.com/python-poetry/poetry-core/pull/659),
[#669](https://github.com/python-poetry/poetry-core/pull/669),
[#678](https://github.com/python-poetry/poetry-core/pull/678),
[#694](https://github.com/python-poetry/poetry-core/pull/694)).
- Rework list of files included in build artifacts ([#666](https://github.com/python-poetry/poetry-core/pull/666)).
- Fix an issue where insignificant errors were printed if the working directory is not inside a git repository ([#684](https://github.com/python-poetry/poetry-core/pull/684)).
- Fix an issue where the project's directory was not recognized as git repository on Windows due to an encoding issue ([#685](https://github.com/python-poetry/poetry-core/pull/685)).


## [1.7.1] - 2023-11-16

### Fixed

- Fix an issue where sdists that call CLI tools of their build requirements could not be installed ([#8630](https://github.com/python-poetry/poetry/pull/8630)).
- Fix an issue where sdists with symlinks could not be installed due to a broken tarfile datafilter ([#8649](https://github.com/python-poetry/poetry/pull/8649)).
- Fix an issue where `poetry init` failed when trying to add dependencies ([#8655](https://github.com/python-poetry/poetry/pull/8655)).
- Fix an issue where `poetry install` failed if `virtualenvs.create` was set to `false` ([#8672](https://github.com/python-poetry/poetry/pull/8672)).


## [1.7.0] - 2023-11-03

### Added

- **Add official support for Python 3.12** ([#7803](https://github.com/python-poetry/poetry/pull/7803), [#8544](https://github.com/python-poetry/poetry/pull/8544)).
- **Print a future warning that `poetry-plugin-export` will not be installed by default anymore** ([#8562](https://github.com/python-poetry/poetry/pull/8562)).
- Add `poetry-install` pre-commit hook ([#8327](https://github.com/python-poetry/poetry/pull/8327)).
- Add `--next-phase` option to `poetry version` ([#8089](https://github.com/python-poetry/poetry/pull/8089)).
- Print a warning when overwriting files from another package at installation ([#8386](https://github.com/python-poetry/poetry/pull/8386)).
- Print a warning if the current project cannot be installed ([#8369](https://github.com/python-poetry/poetry/pull/8369)).
- Report more details on build backend exceptions ([#8464](https://github.com/python-poetry/poetry/pull/8464)).

### Changed

- Set Poetry as `user-agent` for all HTTP requests ([#8394](https://github.com/python-poetry/poetry/pull/8394)).
- Do not install `setuptools` per default in Python 3.12 ([#7803](https://github.com/python-poetry/poetry/pull/7803)).
- Do not install `wheel` per default ([#7803](https://github.com/python-poetry/poetry/pull/7803)).
- Remove `setuptools` and `wheel` when running `poetry install --sync` if they are not required by the project ([#8600](https://github.com/python-poetry/poetry/pull/#8600)).
- Improve error message about PEP-517 support ([#8463](https://github.com/python-poetry/poetry/pull/8463)).
- Improve `keyring` handling ([#8227](https://github.com/python-poetry/poetry/pull/8227)).
- Read the `description` field when extracting metadata from `setup.py` files ([#8545](https://github.com/python-poetry/poetry/pull/8545)).

### Fixed

- **Fix an issue where dependencies of inactive extras were locked and installed** ([#8399](https://github.com/python-poetry/poetry/pull/8399)).
- **Fix an issue where build requirements were not installed due to a race condition in the artifact cache** ([#8517](https://github.com/python-poetry/poetry/pull/8517)).
- Fix an issue where packages included in the system site packages were installed even though `virtualenvs.options.system-site-packages` was set ([#8359](https://github.com/python-poetry/poetry/pull/8359)).
- Fix an issue where git dependencies' submodules with relative URLs were handled incorrectly ([#8020](https://github.com/python-poetry/poetry/pull/8020)).
- Fix an issue where a failed installation of build dependencies was not noticed directly ([#8479](https://github.com/python-poetry/poetry/pull/8479)).
- Fix an issue where `poetry shell` did not work completely with `nushell` ([#8478](https://github.com/python-poetry/poetry/pull/8478)).
- Fix an issue where a confusing error messages was displayed when running `poetry config pypi-token.pypi` without a value ([#8502](https://github.com/python-poetry/poetry/pull/8502)).
- Fix an issue where a cryptic error message is printed if there is no metadata entry in the lockfile ([#8523](https://github.com/python-poetry/poetry/pull/8523)).
- Fix an issue with the encoding with special characters in the virtualenv's path ([#8565](https://github.com/python-poetry/poetry/pull/8565)).
- Fix an issue where the connection pool size was not adjusted to the number of workers ([#8559](https://github.com/python-poetry/poetry/pull/8559)).

### Docs

- Improve the wording regarding a project's supported Python range ([#8423](https://github.com/python-poetry/poetry/pull/8423)).
- Make `pipx` the preferred (first mentioned) installation method ([#8090](https://github.com/python-poetry/poetry/pull/8090)).
- Add a warning about `poetry self` on Windows ([#8090](https://github.com/python-poetry/poetry/pull/8090)).
- Fix example for `poetry add` with a git dependency ([#8438](https://github.com/python-poetry/poetry/pull/8438)).
- Add information about auto-included files in wheels and sdist ([#8555](https://github.com/python-poetry/poetry/pull/8555)).
- Fix documentation of the `POETRY_REPOSITORIES_` variables docs ([#8492](https://github.com/python-poetry/poetry/pull/8492)).
- Add `CITATION.cff` file ([#8510](https://github.com/python-poetry/poetry/pull/8510)).

### poetry-core ([`1.8.1`](https://github.com/python-poetry/poetry-core/releases/tag/1.8.1))

- Add support for creating packages dynamically in the build script ([#629](https://github.com/python-poetry/poetry-core/pull/629)).
- Improve marker logic for `extra` markers ([#636](https://github.com/python-poetry/poetry-core/pull/636)).
- Update list of supported licenses ([#635](https://github.com/python-poetry/poetry-core/pull/635), [#646](https://github.com/python-poetry/poetry-core/pull/646)).
- Fix an issue where projects with extension modules were not installed in editable mode ([#633](https://github.com/python-poetry/poetry-core/pull/633)).
- Fix an issue where the wrong or no `lib` folder was added to the wheel ([#634](https://github.com/python-poetry/poetry-core/pull/634)).

### poetry-plugin-export ([`^1.6.0`](https://github.com/python-poetry/poetry-plugin-export/releases/tag/1.6.0))

- Add an `--all-extras` option ([#241](https://github.com/python-poetry/poetry-plugin-export/pull/241)).
- Fix an issue where git dependencies are exported with the branch name instead of the resolved commit hash ([#213](https://github.com/python-poetry/poetry-plugin-export/pull/213)).


## [1.6.1] - 2023-08-21

### Fixed

- Update the minimum required version of `requests` ([#8336](https://github.com/python-poetry/poetry/pull/8336)).


## [1.6.0] - 2023-08-20

### Added

- **Add support for repositories that do not provide a supported hash algorithm** ([#8118](https://github.com/python-poetry/poetry/pull/8118)).
- **Add full support for duplicate dependencies with overlapping markers** ([#7257](https://github.com/python-poetry/poetry/pull/7257)).
- **Improve performance of `poetry lock` for certain edge cases** ([#8256](https://github.com/python-poetry/poetry/pull/8256)).
- Improve performance of `poetry install` ([#8031](https://github.com/python-poetry/poetry/pull/8031)).
- `poetry check` validates that specified `readme` files do exist ([#7444](https://github.com/python-poetry/poetry/pull/7444)).
- Add a downgrading note when updating to an older version ([#8176](https://github.com/python-poetry/poetry/pull/8176)).
- Add support for `vox` in the `xonsh` shell ([#8203](https://github.com/python-poetry/poetry/pull/8203)).
- Add support for `pre-commit` hooks for projects where the pyproject.toml file is located in a subfolder ([#8204](https://github.com/python-poetry/poetry/pull/8204)).
- Add support for the `git+http://` scheme ([#6619](https://github.com/python-poetry/poetry/pull/6619)).

### Changed

- **Drop support for Python 3.7** ([#7674](https://github.com/python-poetry/poetry/pull/7674)).
- Move `poetry lock --check` to `poetry check --lock` and deprecate the former ([#8015](https://github.com/python-poetry/poetry/pull/8015)).
- Change future warning that PyPI will only be disabled automatically if there are no primary sources ([#8151](https://github.com/python-poetry/poetry/pull/8151)).

### Fixed

- Fix an issue where `build-system.requires` were not respected for projects with build scripts ([#7975](https://github.com/python-poetry/poetry/pull/7975)).
- Fix an issue where the encoding was not handled correctly when calling a subprocess ([#8060](https://github.com/python-poetry/poetry/pull/8060)).
- Fix an issue where `poetry show --top-level` did not show top level dependencies with extras ([#8076](https://github.com/python-poetry/poetry/pull/8076)).
- Fix an issue where `poetry init` handled projects with `src` layout incorrectly ([#8218](https://github.com/python-poetry/poetry/pull/8218)).
- Fix an issue where Poetry wrote `.pth` files with the wrong encoding ([#8041](https://github.com/python-poetry/poetry/pull/8041)).
- Fix an issue where `poetry install` did not respect the source if the same version of a package has been locked from different sources ([#8304](https://github.com/python-poetry/poetry/pull/8304)).

### Docs

- Document **official Poetry badge** ([#8066](https://github.com/python-poetry/poetry/pull/8066)).
- Update configuration folder path for macOS ([#8062](https://github.com/python-poetry/poetry/pull/8062)).
- Add a warning about pip ignoring lock files ([#8117](https://github.com/python-poetry/poetry/pull/8117)).
- Clarify the use of the `virtualenvs.in-project` setting. ([#8126](https://github.com/python-poetry/poetry/pull/8126)).
- Change `pre-commit` YAML style to be consistent with pre-commit's own examples ([#8146](https://github.com/python-poetry/poetry/pull/8146)).
- Fix command for listing installed plugins ([#8200](https://github.com/python-poetry/poetry/pull/8200)).
- Mention the `nox-poetry` package ([#8173](https://github.com/python-poetry/poetry/pull/8173)).
- Add an example with a PyPI source in the pyproject.toml file ([#8171](https://github.com/python-poetry/poetry/pull/8171)).
- Use `reference` instead of deprecated `callable` in the scripts example ([#8211](https://github.com/python-poetry/poetry/pull/8211)).

### poetry-core ([`1.7.0`](https://github.com/python-poetry/poetry-core/releases/tag/1.7.0))

- Improve performance of marker handling ([#609](https://github.com/python-poetry/poetry-core/pull/609)).
- Allow `|` as a value separator in markers with the operators `in` and `not in` ([#608](https://github.com/python-poetry/poetry-core/pull/608)).
- Put pretty name (instead of normalized name) in metadata ([#620](https://github.com/python-poetry/poetry-core/pull/620)).
- Update list of supported licenses ([#623](https://github.com/python-poetry/poetry-core/pull/623)).
- Fix an issue where PEP 508 dependency specifications with names starting with a digit could not be parsed ([#607](https://github.com/python-poetry/poetry-core/pull/607)).
- Fix an issue where Poetry considered an unrelated `.gitignore` file resulting in an empty wheel ([#611](https://github.com/python-poetry/poetry-core/pull/611)).

### poetry-plugin-export ([`^1.5.0`](https://github.com/python-poetry/poetry-plugin-export/releases/tag/1.5.0))

- Fix an issue where markers for dependencies required by an extra were not generated correctly ([#209](https://github.com/python-poetry/poetry-plugin-export/pull/209)).


## [1.5.1] - 2023-05-29

### Added

- Improve dependency resolution performance in cases with a lot of backtracking ([#7950](https://github.com/python-poetry/poetry/pull/7950)).

### Changed

- Disable wheel content validation during installation ([#7987](https://github.com/python-poetry/poetry/pull/7987)).

### Fixed

- Fix an issue where partially downloaded wheels were cached ([#7968](https://github.com/python-poetry/poetry/pull/7968)).
- Fix an issue where `poetry run` did no longer execute relative-path scripts ([#7963](https://github.com/python-poetry/poetry/pull/7963)).
- Fix an issue where dependencies were not installed in `in-project` environments ([#7977](https://github.com/python-poetry/poetry/pull/7977)).
- Fix an issue where no solution was found for a transitive dependency on a pre-release of a package ([#7978](https://github.com/python-poetry/poetry/pull/7978)).
- Fix an issue where cached repository packages were incorrectly parsed, leading to its dependencies being ignored ([#7995](https://github.com/python-poetry/poetry/pull/7995)).
- Fix an issue where an explicit source was ignored so that a direct origin dependency was used instead ([#7973](https://github.com/python-poetry/poetry/pull/7973)).
- Fix an issue where the installation of big wheels consumed a lot of memory ([#7987](https://github.com/python-poetry/poetry/pull/7987)).

### Docs

- Add information about multiple constraints dependencies with direct origin and version dependencies ([#7973](https://github.com/python-poetry/poetry/pull/7973)).

### poetry-core ([`1.6.1`](https://github.com/python-poetry/poetry-core/releases/tag/1.6.1))

- Fix an endless recursion in marker handling ([#593](https://github.com/python-poetry/poetry-core/pull/593)).
- Fix an issue where the wheel tag was not built correctly under certain circumstances ([#591](https://github.com/python-poetry/poetry-core/pull/591)).

### poetry-plugin-export ([`^1.4.0`](https://github.com/python-poetry/poetry-plugin-export/releases/tag/1.4.0))

- Fix an issue where `--extra-index-url` and `--trusted-host` was not generated for sources with priority `explicit` ([#205](https://github.com/python-poetry/poetry-plugin-export/pull/205)).


## [1.5.0] - 2023-05-19

### Added

- **Introduce the new source priorities `explicit` and `supplemental`** ([#7658](https://github.com/python-poetry/poetry/pull/7658),
[#6879](https://github.com/python-poetry/poetry/pull/6879)).
- **Introduce the option to configure the priority of the implicit PyPI source** ([#7801](https://github.com/python-poetry/poetry/pull/7801)).
- Add handling for corrupt cache files ([#7453](https://github.com/python-poetry/poetry/pull/7453)).
- Improve caching of URL and git dependencies ([#7693](https://github.com/python-poetry/poetry/pull/7693),
[#7473](https://github.com/python-poetry/poetry/pull/7473)).
- Add option to skip installing directory dependencies ([#6845](https://github.com/python-poetry/poetry/pull/6845),
[#7923](https://github.com/python-poetry/poetry/pull/7923)).
- Add `--executable` option to `poetry env info` ([#7547](https://github.com/python-poetry/poetry/pull/7547)).
- Add `--top-level` option to `poetry show` ([#7415](https://github.com/python-poetry/poetry/pull/7415)).
- Add `--lock` option to `poetry remove` ([#7917](https://github.com/python-poetry/poetry/pull/7917)).
- Add experimental `POETRY_REQUESTS_TIMEOUT` option ([#7081](https://github.com/python-poetry/poetry/pull/7081)).
- Improve performance of wheel inspection by avoiding unnecessary file copy operations ([#7916](https://github.com/python-poetry/poetry/pull/7916)).

### Changed

- **Remove the old deprecated installer and the corresponding setting `experimental.new-installer`** ([#7356](https://github.com/python-poetry/poetry/pull/7356)).
- **Introduce `priority` key for sources and deprecate flags `default` and `secondary`** ([#7658](https://github.com/python-poetry/poetry/pull/7658)).
- Deprecate `poetry run <entry point>` if the entry point was not previously installed via `poetry install` ([#7606](https://github.com/python-poetry/poetry/pull/7606)).
- Only write the lock file if the installation succeeds ([#7498](https://github.com/python-poetry/poetry/pull/7498)).
- Do not write the unused package category into the lock file ([#7637](https://github.com/python-poetry/poetry/pull/7637)).

### Fixed

- Fix an issue where Poetry's internal pyproject.toml continually grows larger with empty lines ([#7705](https://github.com/python-poetry/poetry/pull/7705)).
- Fix an issue where Poetry crashes due to corrupt cache files ([#7453](https://github.com/python-poetry/poetry/pull/7453)).
- Fix an issue where the `Retry-After` in HTTP responses was not respected and retries were handled inconsistently ([#7072](https://github.com/python-poetry/poetry/pull/7072)).
- Fix an issue where Poetry silently ignored invalid groups ([#7529](https://github.com/python-poetry/poetry/pull/7529)).
- Fix an issue where Poetry does not find a compatible Python version if not given explicitly ([#7771](https://github.com/python-poetry/poetry/pull/7771)).
- Fix an issue where the `direct_url.json` of an editable install from a git dependency was invalid ([#7473](https://github.com/python-poetry/poetry/pull/7473)).
- Fix an issue where error messages from build backends were not decoded correctly ([#7781](https://github.com/python-poetry/poetry/pull/7781)).
- Fix an infinite loop when adding certain dependencies ([#7405](https://github.com/python-poetry/poetry/pull/7405)).
- Fix an issue where pre-commit hooks skip pyproject.toml files in subdirectories ([#7239](https://github.com/python-poetry/poetry/pull/7239)).
- Fix an issue where pre-commit hooks do not use the expected Python version ([#6989](https://github.com/python-poetry/poetry/pull/6989)).
- Fix an issue where an unclear error message is printed if the project name is the same as one of its dependencies ([#7757](https://github.com/python-poetry/poetry/pull/7757)).
- Fix an issue where `poetry install` returns a zero exit status even though the build script failed ([#7812](https://github.com/python-poetry/poetry/pull/7812)).
- Fix an issue where an existing `.venv` was not used if `in-project` was not set ([#7792](https://github.com/python-poetry/poetry/pull/7792)).
- Fix an issue where multiple extras passed to `poetry add` were not parsed correctly ([#7836](https://github.com/python-poetry/poetry/pull/7836)).
- Fix an issue where `poetry shell` did not send a newline to `fish` ([#7884](https://github.com/python-poetry/poetry/pull/7884)).
- Fix an issue where `poetry update --lock` printed operations that were not executed ([#7915](https://github.com/python-poetry/poetry/pull/7915)).
- Fix an issue where `poetry add --lock` did perform a full update of all dependencies ([#7920](https://github.com/python-poetry/poetry/pull/7920)).
- Fix an issue where `poetry shell` did not work with `nushell` ([#7919](https://github.com/python-poetry/poetry/pull/7919)).
- Fix an issue where subprocess calls failed on Python 3.7 ([#7932](https://github.com/python-poetry/poetry/pull/7932)).
- Fix an issue where keyring was called even though the password was stored in an environment variable ([#7928](https://github.com/python-poetry/poetry/pull/7928)).

### Docs

- Add information about what to use instead of `--dev` ([#7647](https://github.com/python-poetry/poetry/pull/7647)).
- Promote semantic versioning less aggressively ([#7517](https://github.com/python-poetry/poetry/pull/7517)).
- Explain Poetry's own versioning scheme in the FAQ ([#7517](https://github.com/python-poetry/poetry/pull/7517)).
- Update documentation for configuration with environment variables ([#6711](https://github.com/python-poetry/poetry/pull/6711)).
- Add details how to disable the virtualenv prompt ([#7874](https://github.com/python-poetry/poetry/pull/7874)).
- Improve documentation on whether to commit `poetry.lock` ([#7506](https://github.com/python-poetry/poetry/pull/7506)).
- Improve documentation of `virtualenv.create` ([#7608](https://github.com/python-poetry/poetry/pull/7608)).

### poetry-core ([`1.6.0`](https://github.com/python-poetry/poetry-core/releases/tag/1.6.0))

- Improve error message for invalid markers ([#569](https://github.com/python-poetry/poetry-core/pull/569)).
- Increase robustness when deleting temporary directories on Windows ([#460](https://github.com/python-poetry/poetry-core/pull/460)).
- Replace `tomlkit` with `tomli`, which changes the interface of some _internal_ classes ([#483](https://github.com/python-poetry/poetry-core/pull/483)).
- Deprecate `Package.category` ([#561](https://github.com/python-poetry/poetry-core/pull/561)).
- Fix a performance regression in marker handling ([#568](https://github.com/python-poetry/poetry-core/pull/568)).
- Fix an issue where wildcard version constraints were not handled correctly ([#402](https://github.com/python-poetry/poetry-core/pull/402)).
- Fix an issue where `poetry build` created duplicate Python classifiers if they were specified manually ([#578](https://github.com/python-poetry/poetry-core/pull/578)).
- Fix an issue where local versions where not handled correctly ([#579](https://github.com/python-poetry/poetry-core/pull/579)).


## [1.4.2] - 2023-04-02

### Changed

- When trying to install wheels with invalid `RECORD` files, Poetry does not fail anymore but only prints a warning.
  This mitigates an unintended change introduced in Poetry 1.4.1 ([#7694](https://github.com/python-poetry/poetry/pull/7694)).

### Fixed

- Fix an issue where relative git submodule urls were not parsed correctly ([#7017](https://github.com/python-poetry/poetry/pull/7017)).
- Fix an issue where Poetry could freeze when building a project with a build script if it generated enough output to fill the OS pipe buffer ([#7699](https://github.com/python-poetry/poetry/pull/7699)).


## [1.4.1] - 2023-03-19

### Fixed

- Fix an issue where `poetry install` did not respect the requirements for building editable dependencies ([#7579](https://github.com/python-poetry/poetry/pull/7579)).
- Fix an issue where `poetry init` crashed due to bad input when adding packages interactively ([#7569](https://github.com/python-poetry/poetry/pull/7569)).
- Fix an issue where `poetry install` ignored the `subdirectory` argument of git dependencies ([#7580](https://github.com/python-poetry/poetry/pull/7580)).
- Fix an issue where installing packages with `no-binary` could result in a false hash mismatch ([#7594](https://github.com/python-poetry/poetry/pull/7594)).
- Fix an issue where the hash of sdists was neither validated nor written to the `direct_url.json` during installation ([#7594](https://github.com/python-poetry/poetry/pull/7594)).
- Fix an issue where `poetry install --sync` attempted to remove itself ([#7626](https://github.com/python-poetry/poetry/pull/7626)).
- Fix an issue where wheels with non-normalized `dist-info` directory names could not be installed ([#7671](https://github.com/python-poetry/poetry/pull/7671)).
- Fix an issue where `poetry install --compile` compiled with optimization level 1 ([#7666](https://github.com/python-poetry/poetry/pull/7666)).

### Docs

- Clarify the behavior of the `--extras` option ([#7563](https://github.com/python-poetry/poetry/pull/7563)).
- Expand the FAQ on reasons for slow dependency resolution ([#7620](https://github.com/python-poetry/poetry/pull/7620)).


### poetry-core ([`1.5.2`](https://github.com/python-poetry/poetry-core/releases/tag/1.5.2))

- Fix an issue where wheels built on Windows could contain duplicate entries in the RECORD file ([#555](https://github.com/python-poetry/poetry-core/pull/555)).


## [1.4.0] - 2023-02-27

### Added

- **Add a modern installer (`installer.modern-installation`) for faster installation of packages and independence from pip** ([#6205](https://github.com/python-poetry/poetry/pull/6205)).
- Add support for `Private ::` trove classifiers ([#7271](https://github.com/python-poetry/poetry/pull/7271)).
- Add the version of poetry in the `@generated` comment at the beginning of the lock file ([#7339](https://github.com/python-poetry/poetry/pull/7339)).
- Add support for `virtualenvs.prefer-active-python` when running `poetry new` and `poetry init` ([#7100](https://github.com/python-poetry/poetry/pull/7100)).

### Changed

- **Deprecate the old installer, i.e. setting `experimental.new-installer` to `false`** ([#7358](https://github.com/python-poetry/poetry/pull/7358)).
- Remove unused `platform` field from cached package info and bump the cache version ([#7304](https://github.com/python-poetry/poetry/pull/7304)).
- Extra dependencies of the root project are now sorted in the lock file ([#7375](https://github.com/python-poetry/poetry/pull/7375)).
- Remove upper boundary for `importlib-metadata` dependency ([#7434](https://github.com/python-poetry/poetry/pull/7434)).
- Validate path dependencies during use instead of during construction ([#6844](https://github.com/python-poetry/poetry/pull/6844)).
- Remove the deprecated `repository` modules ([#7468](https://github.com/python-poetry/poetry/pull/7468)).

### Fixed

- Fix an issue where an unconditional dependency of an extra was not installed in specific environments ([#7175](https://github.com/python-poetry/poetry/pull/7175)).
- Fix an issue where a pre-release of a dependency was chosen even if a stable release fulfilled the constraint ([#7225](https://github.com/python-poetry/poetry/pull/7225), [#7236](https://github.com/python-poetry/poetry/pull/7236)).
- Fix an issue where HTTP redirects were not handled correctly during publishing ([#7160](https://github.com/python-poetry/poetry/pull/7160)).
- Fix an issue where `poetry check` did not handle the `-C, --directory` option correctly ([#7241](https://github.com/python-poetry/poetry/pull/7241)).
- Fix an issue where the subdirectory information of a git dependency was not written to the lock file ([#7367](https://github.com/python-poetry/poetry/pull/7367)).
- Fix an issue where the wrong Python version was selected when creating an virtual environment ([#7221](https://github.com/python-poetry/poetry/pull/7221)).
- Fix an issue where packages that should be kept were uninstalled when calling `poetry install --sync` ([#7389](https://github.com/python-poetry/poetry/pull/7389)).
- Fix an issue where an incorrect value was set for `sys.argv[0]` when running installed scripts ([#6737](https://github.com/python-poetry/poetry/pull/6737)).
- Fix an issue where hashes in `direct_url.json` files were not written according to the specification ([#7475](https://github.com/python-poetry/poetry/pull/7475)).
- Fix an issue where poetry commands failed due to special characters in the path of the project or virtual environment ([#7471](https://github.com/python-poetry/poetry/pull/7471)).
- Fix an issue where poetry crashed with a `JSONDecodeError` when running a Python script that produced certain warnings ([#6665](https://github.com/python-poetry/poetry/pull/6665)).

### Docs

- Add advice on how to maintain a poetry plugin ([#6977](https://github.com/python-poetry/poetry/pull/6977)).
- Update tox examples to comply with the latest tox release ([#7341](https://github.com/python-poetry/poetry/pull/7341)).
- Mention that the `poetry export` can export `constraints.txt` files ([#7383](https://github.com/python-poetry/poetry/pull/7383)).
- Add clarifications for moving configuration files ([#6864](https://github.com/python-poetry/poetry/pull/6864)).
- Mention the different types of exact version specifications ([#7503](https://github.com/python-poetry/poetry/pull/7503)).

### poetry-core ([`1.5.1`](https://github.com/python-poetry/poetry-core/releases/tag/1.5.1))

- Improve marker handling ([#528](https://github.com/python-poetry/poetry-core/pull/528),
[#534](https://github.com/python-poetry/poetry-core/pull/534),
[#530](https://github.com/python-poetry/poetry-core/pull/530),
[#546](https://github.com/python-poetry/poetry-core/pull/546),
[#547](https://github.com/python-poetry/poetry-core/pull/547)).
- Validate whether dependencies referenced in `extras` are defined in the main dependency group ([#542](https://github.com/python-poetry/poetry-core/pull/542)).
- Poetry no longer generates a `setup.py` file in sdists by default ([#318](https://github.com/python-poetry/poetry-core/pull/318)).
- Fix an issue where trailing newlines were allowed in `tool.poetry.description` ([#505](https://github.com/python-poetry/poetry-core/pull/505)).
- Fix an issue where the name of the data folder in wheels was not normalized ([#532](https://github.com/python-poetry/poetry-core/pull/532)).
- Fix an issue where the order of entries in the RECORD file was not deterministic ([#545](https://github.com/python-poetry/poetry-core/pull/545)).
- Fix an issue where zero padding was not correctly handled in version comparisons ([#540](https://github.com/python-poetry/poetry-core/pull/540)).
- Fix an issue where sdist builds did not support multiple READMEs ([#486](https://github.com/python-poetry/poetry-core/pull/486)).

### poetry-plugin-export ([`^1.3.0`](https://github.com/python-poetry/poetry-plugin-export/releases/tag/1.3.0))

- Fix an issue where the export failed if there was a circular dependency on the root package ([#118](https://github.com/python-poetry/poetry-plugin-export/pull/118)).


## [1.3.2] - 2023-01-10

### Fixed

- Fix a performance regression when locking dependencies from PyPI ([#7232](https://github.com/python-poetry/poetry/pull/7232)).
- Fix an issue where passing a relative path via `-C, --directory` fails ([#7266](https://github.com/python-poetry/poetry/pull/7266)).

### Docs

- Update docs to reflect the removal of the deprecated `get-poetry.py` installer from the repository ([#7288](https://github.com/python-poetry/poetry/pull/7288)).
- Add clarifications for `virtualenvs.path` settings ([#7286](https://github.com/python-poetry/poetry/pull/7286)).


## [1.3.1] - 2022-12-12

### Fixed

- Fix an issue where an explicit dependency on `lockfile` was missing, resulting in a broken Poetry in rare circumstances ([7169](https://github.com/python-poetry/poetry/pull/7169)).


## [1.3.0] - 2022-12-09

### Added

- Mark the lock file with an `@generated` comment as used by common tooling ([#2773](https://github.com/python-poetry/poetry/pull/2773)).
- `poetry check` validates trove classifiers and warns for deprecations ([#2881](https://github.com/python-poetry/poetry/pull/2881)).
- Introduce a top level `-C, --directory` option to set the working path ([#6810](https://github.com/python-poetry/poetry/pull/6810)).

### Changed

- **New lock file format (version 2.0)** ([#6393](https://github.com/python-poetry/poetry/pull/6393)).
- Path dependency metadata is unconditionally re-locked ([#6843](https://github.com/python-poetry/poetry/pull/6843)).
- URL dependency hashes are locked ([#7121](https://github.com/python-poetry/poetry/pull/7121)).
- `poetry update` and `poetry lock` should now resolve dependencies more similarly ([#6477](https://github.com/python-poetry/poetry/pull/6477)).
- `poetry publish` will report more useful errors when a file does not exist ([#4417](https://github.com/python-poetry/poetry/pull/4417)).
- `poetry add` will check for duplicate entries using canonical names ([#6832](https://github.com/python-poetry/poetry/pull/6832)).
- Wheels are preferred to source distributions when gathering metadata ([#6547](https://github.com/python-poetry/poetry/pull/6547)).
- Git dependencies of extras are only fetched if the extra is requested ([#6615](https://github.com/python-poetry/poetry/pull/6615)).
- Invoke `pip` with `--no-input` to prevent hanging without feedback ([#6724](https://github.com/python-poetry/poetry/pull/6724), [#6966](https://github.com/python-poetry/poetry/pull/6966)).
- Invoke `pip` with `--isolated` to prevent the influence of user configuration ([#6531](https://github.com/python-poetry/poetry/pull/6531)).
- Interrogate environments with Python in isolated (`-I`) mode ([#6628](https://github.com/python-poetry/poetry/pull/6628)).
- Raise an informative error when multiple version constraints overlap and are incompatible ([#7098](https://github.com/python-poetry/poetry/pull/7098)).

### Fixed

- **Fix an issue where concurrent instances of Poetry would corrupt the artifact cache** ([#6186](https://github.com/python-poetry/poetry/pull/6186)).
- **Fix an issue where Poetry can hang after being interrupted due to stale locking in cache** ([#6471](https://github.com/python-poetry/poetry/pull/6471)).
- Fix an issue where the output of commands executed with `--dry-run` contained duplicate entries ([#4660](https://github.com/python-poetry/poetry/pull/4660)).
- Fix an issue where `requests`'s pool size did not match the number of installer workers ([#6805](https://github.com/python-poetry/poetry/pull/6805)).
- Fix an issue where `poetry show --outdated` failed with a runtime error related to direct origin dependencies ([#6016](https://github.com/python-poetry/poetry/pull/6016)).
- Fix an issue where only the last command of an `ApplicationPlugin` is registered ([#6304](https://github.com/python-poetry/poetry/pull/6304)).
- Fix an issue where git dependencies were fetched unnecessarily when running `poetry lock --no-update` ([#6131](https://github.com/python-poetry/poetry/pull/6131)).
- Fix an issue where stdout was polluted with messages that should go to stderr ([#6429](https://github.com/python-poetry/poetry/pull/6429)).
- Fix an issue with `poetry shell` activation and zsh ([#5795](https://github.com/python-poetry/poetry/pull/5795)).
- Fix an issue where a url dependencies were shown as outdated ([#6396](https://github.com/python-poetry/poetry/pull/6396)).
- Fix an issue where the `source` field of a dependency with extras was ignored ([#6472](https://github.com/python-poetry/poetry/pull/6472)).
- Fix an issue where a package from the wrong source was installed for a multiple-constraints dependency with different sources ([#6747](https://github.com/python-poetry/poetry/pull/6747)).
- Fix an issue where dependencies from different sources where merged during dependency resolution ([#6679](https://github.com/python-poetry/poetry/pull/6679)).
- Fix an issue where `experimental.system-git-client` could not be used via environment variable ([#6783](https://github.com/python-poetry/poetry/pull/6783)).
- Fix an issue where Poetry fails with an `AssertionError` due to `distribution.files` being `None` ([#6788](https://github.com/python-poetry/poetry/pull/6788)).
- Fix an issue where `poetry env info` did not respect `virtualenvs.prefer-active-python` ([#6986](https://github.com/python-poetry/poetry/pull/6986)).
- Fix an issue where `poetry env list` does not list the in-project environment ([#6979](https://github.com/python-poetry/poetry/pull/6979)).
- Fix an issue where `poetry env remove` removed the wrong environment ([#6195](https://github.com/python-poetry/poetry/pull/6195)).
- Fix an issue where the return code of a script was not relayed as exit code ([#6824](https://github.com/python-poetry/poetry/pull/6824)).
- Fix an issue where the solver could silently swallow `ValueError` ([#6790](https://github.com/python-poetry/poetry/pull/6790)).

### Docs

- Improve documentation of package sources ([#5605](https://github.com/python-poetry/poetry/pull/5605)).
- Correct the default cache path on Windows ([#7012](https://github.com/python-poetry/poetry/pull/7012)).

### poetry-core ([`1.4.0`](https://github.com/python-poetry/poetry-core/releases/tag/1.4.0))

- The PEP 517 `metadata_directory` is now respected as an input to the `build_wheel` hook ([#487](https://github.com/python-poetry/poetry-core/pull/487)).
- `ParseConstraintError` is now raised on version and constraint parsing errors, and includes information on the package that caused the error ([#514](https://github.com/python-poetry/poetry-core/pull/514)).
- Fix an issue where invalid PEP 508 requirements were generated due to a missing space before semicolons ([#510](https://github.com/python-poetry/poetry-core/pull/510)).
- Fix an issue where relative paths were encoded into package requirements, instead of a file:// URL as required by PEP 508 ([#512](https://github.com/python-poetry/poetry-core/pull/512)).

### poetry-plugin-export ([`^1.2.0`](https://github.com/python-poetry/poetry-plugin-export/releases/tag/1.2.0))

- Ensure compatibility with Poetry 1.3.0. No functional changes.

### cleo ([`^2.0.0`](https://github.com/python-poetry/poetry-core/releases/tag/2.0.0))

- Fix an issue where shell completions had syntax errors ([#247](https://github.com/python-poetry/cleo/pull/247)).
- Fix an issue where not reading all the output of a command resulted in a "Broken pipe" error ([#165](https://github.com/python-poetry/cleo/pull/165)).
- Fix an issue where errors were not shown in non-verbose mode ([#166](https://github.com/python-poetry/cleo/pull/166)).


## [1.2.2] - 2022-10-10

### Added

- Add forward compatibility for lock file format 2.0, which will be used by Poetry 1.3 ([#6608](https://github.com/python-poetry/poetry/pull/6608)).

### Changed

- Allow `poetry lock` to re-generate the lock file when invalid or incompatible ([#6753](https://github.com/python-poetry/poetry/pull/6753)).

### Fixed

- Fix an issue where the deprecated JSON API was used to query PyPI for available versions of a package ([#6081](https://github.com/python-poetry/poetry/pull/6081)).
- Fix an issue where versions were escaped wrongly when building the wheel name ([#6476](https://github.com/python-poetry/poetry/pull/6476)).
- Fix an issue where the installation of dependencies failed if pip is a dependency and is updated in parallel to other dependencies ([#6582](https://github.com/python-poetry/poetry/pull/6582)).
- Fix an issue where the names of extras were not normalized according to PEP 685 ([#6541](https://github.com/python-poetry/poetry/pull/6541)).
- Fix an issue where sdist names were not normalized ([#6621](https://github.com/python-poetry/poetry/pull/6621)).
- Fix an issue where invalid constraints, which are ignored, were only reported in a debug message instead of a warning ([#6730](https://github.com/python-poetry/poetry/pull/6730)).
- Fix an issue where `poetry shell` was broken in git bash on Windows ([#6560](https://github.com/python-poetry/poetry/pull/6560)).

### Docs

- Rework the README and contribution docs ([#6552](https://github.com/python-poetry/poetry/pull/6552)).
- Fix for inconsistent docs for multiple-constraint dependencies ([#6604](https://github.com/python-poetry/poetry/pull/6604)).
- Rephrase plugin configuration ([#6557](https://github.com/python-poetry/poetry/pull/6557)).
- Add a note about publishable repositories to `publish` ([#6641](https://github.com/python-poetry/poetry/pull/6641)).
- Fix the path for lazy-loaded bash completion ([#6656](https://github.com/python-poetry/poetry/pull/6656)).
- Fix a reference to the invalid option `--require` ([#6672](https://github.com/python-poetry/poetry/pull/6672)).
- Add a PowerShell one-liner to the basic usage section ([#6683](https://github.com/python-poetry/poetry/pull/6683)).
- Fix the minimum poetry version in the example for plugins ([#6739](https://github.com/python-poetry/poetry/pull/6739)).

### poetry-core ([`1.3.2`](https://github.com/python-poetry/poetry-core/releases/tag/1.3.2))

- Add `3.11` to the list of available Python versions ([#477](https://github.com/python-poetry/poetry-core/pull/477)).
- Fix an issue where caret constraints of pre-releases with a major version of 0 resulted in an empty version range ([#475](https://github.com/python-poetry/poetry-core/pull/475)).

### poetry-plugin-export ([`^1.1.2`](https://github.com/python-poetry/poetry-plugin-export/releases/tag/1.1.2))

- Add support for exporting `constraints.txt` files ([#128](https://github.com/python-poetry/poetry-plugin-export/pull/128)).
- Fix an issue where a relative path passed via `-o` was not interpreted relative to the current working directory ([#130](https://github.com/python-poetry/poetry-plugin-export/pull/130)).


## [1.2.1] - 2022-09-16

### Changed

- Bump `poetry-core` to [`1.2.0`](https://github.com/python-poetry/poetry-core/releases/tag/1.2.0).
- Bump `poetry-plugin-export` to [`^1.0.7`](https://github.com/python-poetry/poetry-plugin-export/releases/tag/1.0.7).

### Fixed

- Fix an issue where `poetry cache clear` did not respect the `-n/--no-interaction` flag ([#6338](https://github.com/python-poetry/poetry/pull/6338)).
- Fix an issue where `poetry lock --no-update` updated dependencies from non-PyPI package sources ([#6335](https://github.com/python-poetry/poetry/pull/6335)).
- Fix a `poetry install` performance regression by falling back to internal pip ([#6062](https://github.com/python-poetry/poetry/pull/6062)).
- Fix an issue where a virtual environment was created unnecessarily when running `poetry export` ([#6282](https://github.com/python-poetry/poetry/pull/6282)).
- Fix an issue where `poetry lock --no-update` added duplicate hashes to the lock file ([#6389](https://github.com/python-poetry/poetry/pull/6389)).
- Fix an issue where `poetry install` fails because of missing hashes for `url` dependencies ([#6389](https://github.com/python-poetry/poetry/pull/6389)).
- Fix an issue where Poetry was not able to update pip in Windows virtual environments ([#6430](https://github.com/python-poetry/poetry/pull/6430)).
- Fix an issue where Poetry was not able to install releases that contained less common link types ([#5767](https://github.com/python-poetry/poetry/pull/5767)).
- Fix a `poetry lock` performance regression when checking non-PyPI sources for yanked versions ([#6442](https://github.com/python-poetry/poetry/pull/6442)).
- Fix an issue where `--no-cache` was not respected when running `poetry install` ([#6479](https://github.com/python-poetry/poetry/pull/6479)).
- Fix an issue where deprecation warnings for `--dev` were missing ([#6475](https://github.com/python-poetry/poetry/pull/6475)).
- Fix an issue where Git dependencies failed to clone when `insteadOf` was used in `.gitconfig` using the Dulwich Git client ([#6506](https://github.com/python-poetry/poetry/pull/6506)).
- Fix an issue where no cache entry is found when calling `poetry cache clear` with a non-normalized package name ([#6537](https://github.com/python-poetry/poetry/pull/6537)).
- Fix an invalid virtualenv constraint on Poetry ([#6402](https://github.com/python-poetry/poetry/pull/6402)).
- Fix outdated build system requirements for Poetry ([#6509](https://github.com/python-poetry/poetry/pull/6509)).

### Docs

- Add missing path segment to paths used by install.python-poetry.org ([#6311](https://github.com/python-poetry/poetry/pull/6311)).
- Add recommendations about how to install Poetry in a CI environment ([#6345](https://github.com/python-poetry/poetry/pull/6345)).
- Fix examples for `--with` and `--without` ([#6318](https://github.com/python-poetry/poetry/pull/6318)).
- Update configuration folder path for macOS ([#6395](https://github.com/python-poetry/poetry/pull/6395)).
- Improve the description of the `virtualenv.create` option ([#6460](https://github.com/python-poetry/poetry/pull/6460)).
- Clarify that `poetry install` removes dependencies of non-installed extras ([#6229](https://github.com/python-poetry/poetry/pull/6229)).
- Add a note about `pre-commit autoupdate` and Poetry's hooks ([#6497](https://github.com/python-poetry/poetry/pull/6497)).


## [1.2.0] - 2022-08-31

### Docs

- Added note about how to add a git dependency with a subdirectory ([#6218](https://github.com/python-poetry/poetry/pull/6218))
- Fixed several style issues in the docs ([#6254](https://github.com/python-poetry/poetry/pull/6254))
- Fixed outdated info about `--only` parameter ([#6263](https://github.com/python-poetry/poetry/pull/6263))


## [1.2.0rc2] - 2022-08-26

### Fixed

- Fixed an issue where virtual environments were created unnecessarily when running `poetry self` commands ([#6225](https://github.com/python-poetry/poetry/pull/6225))
- Ensure that packages' `pretty_name` are written to the lock file ([#6237](https://github.com/python-poetry/poetry/pull/6237))

### Improvements

- Improved the consistency of `Pool().remove_repository()` to make it easier to write poetry plugins ([#6214](https://github.com/python-poetry/poetry/pull/6214))

### Docs

- Removed mentions of Python 2.7 from docs ([#6234](https://github.com/python-poetry/poetry/pull/6234))
- Added note about the difference between groups and extras ([#6230](https://github.com/python-poetry/poetry/pull/6230))


## [1.2.0rc1] - 2022-08-22

### Added

- Added support for subdirectories in git dependencies ([#5172](https://github.com/python-poetry/poetry/pull/5172))
- Added support for yanked releases and files (PEP-592) ([#5841](https://github.com/python-poetry/poetry/pull/5841))
- Virtual environments can now be created even with empty project names ([#5856](https://github.com/python-poetry/poetry/pull/5856))
- Added support for `nushell` in `poetry shell` ([#6063](https://github.com/python-poetry/poetry/pull/6063))

### Changed

- Poetry now falls back to gather metadata for dependencies via pep517 if parsing `pyproject.toml` fails ([#5834](https://github.com/python-poetry/poetry/pull/5834))
- Replaced Poetry's helper method `canonicalize_name()` with `packaging.utils.canonicalize_name()` ([#6022](https://github.com/python-poetry/poetry/pull/6022))
- Removed code for the `export` command, which is now provided via plugin ([#6128](https://github.com/python-poetry/poetry/pull/6128))
- Extras and extras dependencies are now sorted in the lock file ([#6169](https://github.com/python-poetry/poetry/pull/6169))
- Removed deprecated (1.2-only) CLI options ([#6210](https://github.com/python-poetry/poetry/pull/6210))

### Fixed

- Fixed an issue where symlinks in the lock file were not resolved ([#5850](https://github.com/python-poetry/poetry/pull/5850))
- Fixed a `tomlkit` regression resulting in inconsistent line endings ([#5870](https://github.com/python-poetry/poetry/pull/5870))
- Fixed an issue where the `POETRY_PYPI_TOKEN_PYPI` environment variable wasn't respected ([#5911](https://github.com/python-poetry/poetry/pull/5911))
- Fixed an issue where neither Python nor a managed venv can be found, when using Python from MS Store ([#5931](https://github.com/python-poetry/poetry/pull/5931))
- Improved error message of `poetry publish` in the event of an upload error ([#6043](https://github.com/python-poetry/poetry/pull/6043))
- Fixed an issue where `poetry lock` fails without output ([#6058](https://github.com/python-poetry/poetry/pull/6058))
- Fixed an issue where Windows drive mappings break virtual environment names ([#6110](https://github.com/python-poetry/poetry/pull/6110))
- `tomlkit` versions with memory leak are now avoided ([#6160](https://github.com/python-poetry/poetry/pull/6160))
- Fixed an infinite loop in the solver ([#6178](https://github.com/python-poetry/poetry/pull/6178))
- Fixed an issue where latest version was used instead of locked one for vcs dependencies with extras ([#6185](https://github.com/python-poetry/poetry/pull/6185))

### Docs

- Document use of the `subdirectory` parameter ([#5949](https://github.com/python-poetry/poetry/pull/5949))
- Document suggested `tox` config for different use cases ([#6026](https://github.com/python-poetry/poetry/pull/6026))


## [1.1.15] - 2022-08-22

### Changed

- Poetry now fallback to gather metadata for dependencies via pep517 if parsing pyproject.toml fail ([#6206](https://github.com/python-poetry/poetry/pull/6206))
- Extras and extras dependencies are now sorted in lock file ([#6207](https://github.com/python-poetry/poetry/pull/6207))


## [1.2.0b3] - 2022-07-13

**Important**: This release fixes a critical issue that prevented hashes from being retrieved when locking dependencies,
due to a breaking change on PyPI JSON API (see [#5972](https://github.com/python-poetry/poetry/pull/5972)
and [the upstream change](https://github.com/pypi/warehouse/pull/11775) for more details).

After upgrading, you have to clear Poetry cache manually to get that feature working correctly again:

```bash
$ poetry cache clear pypi --all
```

### Added

- Added `--only-root` to `poetry install` to install a project without its
  dependencies ([#5783](https://github.com/python-poetry/poetry/pull/5783))

### Changed

- Improved user experience of `poetry init` ([#5838](https://github.com/python-poetry/poetry/pull/5838))
- Added default timeout for all HTTP requests, to avoid hanging
  requests ([#5881](https://github.com/python-poetry/poetry/pull/5881))
- Updated `poetry init` to better specify how to skip adding
  dependencies ([#5946](https://github.com/python-poetry/poetry/pull/5946))
- Updated Poetry repository names to avoid clashes with user-defined
  repositories ([#5910](https://github.com/python-poetry/poetry/pull/5910))

### Fixed

- Fixed an issue where extras where not handled if they did not match the case-sensitive name of the
  packages ([#4122](https://github.com/python-poetry/poetry/pull/4122))
- Fixed configuration of `experimental.system-git-client` option
  through `poetry config` ([#5818](https://github.com/python-poetry/poetry/pull/5818))
- Fixed uninstallation of git dependencies on Windows ([#5836](https://github.com/python-poetry/poetry/pull/5836))
- Fixed an issue where `~` was not correctly expanded
  in `virtualenvs.path` ([#5848](https://github.com/python-poetry/poetry/pull/5848))
- Fixed an issue where installing/locking dependencies would hang when setting an incorrect git
  repository ([#5880](https://github.com/python-poetry/poetry/pull/5880))
- Fixed an issue in `poetry publish` when keyring was not properly
  configured ([#5889](https://github.com/python-poetry/poetry/pull/5889))
- Fixed duplicated line output in console ([#5890](https://github.com/python-poetry/poetry/pull/5890))
- Fixed an issue where the same wheels where downloaded multiple times during
  installation ([#5871](https://github.com/python-poetry/poetry/pull/5871))
- Fixed an issue where dependencies hashes could not be retrieved when locking due to a breaking change on PyPI JSON
  API ([#5973](https://github.com/python-poetry/poetry/pull/5973))
- Fixed an issue where a dependency with non-requested extras could not be installed if it is requested with extras by
  another dependency ([#5770](https://github.com/python-poetry/poetry/pull/5770))
- Updated git backend to correctly read local/global git config when using dulwich as a git
  backend ([#5935](https://github.com/python-poetry/poetry/pull/5935))
- Fixed an issue where optional dependencies where not correctly exported when defining
  groups ([#5819](https://github.com/python-poetry/poetry/pull/5819))

### Docs

- Fixed configuration instructions for repositories
  specification ([#5809](https://github.com/python-poetry/poetry/pull/5809))
- Added a link to dependency specification
  from `pyproject.toml` ([#5815](https://github.com/python-poetry/poetry/pull/5815))
- Improved `zsh` autocompletion instructions ([#5859](https://github.com/python-poetry/poetry/pull/5859))
- Improved installation and update documentations ([#5857](https://github.com/python-poetry/poetry/pull/5857))
- Improved exact requirements documentation ([#5874](https://github.com/python-poetry/poetry/pull/5874))
- Added documentation for `@` operator ([#5822](https://github.com/python-poetry/poetry/pull/5822))
- Improved autocompletion documentation ([#5879](https://github.com/python-poetry/poetry/pull/5879))
- Improved `scripts` definition documentation ([#5884](https://github.com/python-poetry/poetry/pull/5884))


## [1.1.14] - 2022-07-08

### Fixed

- Fixed an issue where dependencies hashes could not be retrieved when locking due to a breaking change on PyPI JSON API ([#5973](https://github.com/python-poetry/poetry/pull/5973))


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
- Added a new `installer.max-workers` property to the configuration ([#3516](https://github.com/python-poetry/poetry/pull/3516)).
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



[Unreleased]: https://github.com/python-poetry/poetry/compare/1.8.0...master
[1.8.0]: https://github.com/python-poetry/poetry/releases/tag/1.8.0
[1.7.1]: https://github.com/python-poetry/poetry/releases/tag/1.7.1
[1.7.0]: https://github.com/python-poetry/poetry/releases/tag/1.7.0
[1.6.1]: https://github.com/python-poetry/poetry/releases/tag/1.6.1
[1.6.0]: https://github.com/python-poetry/poetry/releases/tag/1.6.0
[1.5.1]: https://github.com/python-poetry/poetry/releases/tag/1.5.1
[1.5.0]: https://github.com/python-poetry/poetry/releases/tag/1.5.0
[1.4.2]: https://github.com/python-poetry/poetry/releases/tag/1.4.2
[1.4.1]: https://github.com/python-poetry/poetry/releases/tag/1.4.1
[1.4.0]: https://github.com/python-poetry/poetry/releases/tag/1.4.0
[1.3.2]: https://github.com/python-poetry/poetry/releases/tag/1.3.2
[1.3.1]: https://github.com/python-poetry/poetry/releases/tag/1.3.1
[1.3.0]: https://github.com/python-poetry/poetry/releases/tag/1.3.0
[1.2.2]: https://github.com/python-poetry/poetry/releases/tag/1.2.2
[1.2.1]: https://github.com/python-poetry/poetry/releases/tag/1.2.1
[1.2.0]: https://github.com/python-poetry/poetry/releases/tag/1.2.0
[1.2.0rc2]: https://github.com/python-poetry/poetry/releases/tag/1.2.0rc2
[1.2.0rc1]: https://github.com/python-poetry/poetry/releases/tag/1.2.0rc1
[1.2.0b3]: https://github.com/python-poetry/poetry/releases/tag/1.2.0b3
[1.2.0b2]: https://github.com/python-poetry/poetry/releases/tag/1.2.0b2
[1.2.0b1]: https://github.com/python-poetry/poetry/releases/tag/1.2.0b1
[1.2.0a2]: https://github.com/python-poetry/poetry/releases/tag/1.2.0a2
[1.2.0a1]: https://github.com/python-poetry/poetry/releases/tag/1.2.0a1
[1.1.14]: https://github.com/python-poetry/poetry/releases/tag/1.1.14
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
