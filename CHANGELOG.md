# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

…

### Changed

…

### Removed

…

## [3000.2.2] - 2026-02-13

### Changed

- fix: tweak setuptools config after rename ([579567d])

## [3000.2.1] - 2026-02-12

### Added

- chore: add build recipe ([4de6b3e])
- ci: add zizmor action ([e5a453a])

### Changed

- chore: rename package to fix name collision ([2fbb13e])
- chore: use modern generics syntax ([bd2994a])
- chore(deps): update dependencies ([ed45385])
- chore(deps): bump actions/checkout from 5 to 6 ([94d14ec])
- ci: fix zizmor findings ([fccaa88])

## [3000.2.0] - 2025-11-24

### Added

- feat: make logging configurable by library users ([6df3acd])
- chore: add license file, headers and info in pyproject.toml ([f18dfe9])

## [3000.1.1] - 2025-11-20

### Added

- chore: add pypi classifiers and license marker to pyproject.toml ([9688a7c])

## [3000.1.0] - 2025-11-19

### Added

- feat: add support for other PostgreSQL connection schemes ([50b4692])

## [3000.0.2] - 2025-11-19

### Added

- feat: add `py.typed` marker file ([981fc8f])

### Changed

- fix: do not log a warning if dev mode is disabled ([0ddc16a])

## [3000.0.1] - 2025-11-17

### Added

- feat: export `ConfigatorSettings` at top level through `__init__.py` ([7569cb8])

### Removed

- fix: remove `print` debug statements from `core._hydrate_field` ([5ddbe83])

## [3000.0.0] - 2025-11-16

Initial release.

<!-- markdownlint-disable-file MD024 -->

[Unreleased]: https://github.com/Utiligize/configator-op/compare/v3000.2.2...HEAD
[3000.2.2]: https://github.com/Utiligize/configator-op/compare/v3000.2.1...v3000.2.2
[3000.2.1]: https://github.com/Utiligize/configator-op/compare/v3000.2.0...v3000.2.1
[3000.2.0]: https://github.com/Utiligize/configator-op/compare/v3000.1.1...v3000.2.0
[3000.1.1]: https://github.com/Utiligize/configator-op/compare/v3000.1.0...v3000.1.1
[3000.1.0]: https://github.com/Utiligize/configator-op/compare/v3000.0.2...v3000.1.0
[3000.0.2]: https://github.com/Utiligize/configator-op/compare/v3000.0.1...v3000.0.2
[3000.0.1]: https://github.com/Utiligize/configator-op/compare/v3000.0.0...v3000.0.1
[3000.0.0]: https://github.com/Utiligize/configator-op/releases/tag/v3000.0.0

<!-- only slugs below here -->
[2fbb13e]: https://github.com/Utiligize/configator-op/commit/2fbb13e9ab59dd72fce7f8d70cde51398d75f814
[4de6b3e]: https://github.com/Utiligize/configator-op/commit/4de6b3e5bcc06d921f3c263dd692c5ecdf95762c
[579567d]: https://github.com/Utiligize/configator-op/commit/579567d6bd872896f25d8f0b8f9e2773407bcb59
[94d14ec]: https://github.com/Utiligize/configator-op/commit/94d14eccdec1257c717d4becae2b8e7f39a4add2
[bd2994a]: https://github.com/Utiligize/configator-op/commit/bd2994a26c44b0036d96ea0b1b28be0862a2597d
[e5a453a]: https://github.com/Utiligize/configator-op/commit/e5a453ac59fe11fbea083b9168289ef111424dc4
[ed45385]: https://github.com/Utiligize/configator-op/commit/ed45385e514b42f2d0e86391cff416086e175ea4
[fccaa88]: https://github.com/Utiligize/configator-op/commit/fccaa88d0f869a204fcc0af0a0340b8cc1577dc7
[0ddc16a]: https://github.com/Utiligize/configator-op/commit/0ddc16ac3e8e0637137bf93146630198215d6546
[50b4692]: https://github.com/Utiligize/configator-op/commit/50b469283ea63937d8993c8b70aa1a164f32b55f
[5ddbe83]: https://github.com/Utiligize/configator-op/commit/5ddbe839ddbb42fe72c1d5acffa2751ced5f967c
[6df3acd]: https://github.com/Utiligize/configator-op/commit/6df3acdef891c6b60b90ea96c128b317956b1671
[7569cb8]: https://github.com/Utiligize/configator-op/commit/7569cb8540028800570513411a5ab5291ab45cc6
[9688a7c]: https://github.com/Utiligize/configator-op/commit/9688a7c1da90d13ce2d54bd270ab6a7e3f3e5de1
[981fc8f]: https://github.com/Utiligize/configator-op/commit/981fc8f4087cef661888e93bf8d147a085f04dc6
[f18dfe9]: https://github.com/Utiligize/configator-op/commit/f18dfe9db79c03fe90cc27535b764e2b55af5942
