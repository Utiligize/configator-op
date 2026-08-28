# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- feat: typed exception hierarchy ([1be6eb3])

## [3000.6.0] - 2026-08-18

### Added

- feat: retry 1Password calls ([5e63002])
- feat: guard CONFIGATOR_DEV_MODE against production activation ([15b1a43])
- docs: add SECURITY.md with private disclosure policy ([397b932])

### Changed

- build: replace mypy with Pyrefly for type checking ([7844a80])
- chore: drop auto uv sync from .envrc on directory entry ([af8a42b])
- chore: update python dependencies ([82c2a30], [168fe4f], [99405f2])
- chore(ci): Update actions/checkout digest to 3d3c42e ([0efeae6], [8d197e2])
- chore(ci): Update all non-major updates ([7912d7f])
- chore(ci): Update astral-sh/setup-uv action to v8.3.2 ([6e2571b])
- chore(ci): Update astral-sh/setup-uv action to v9 ([387f552])
- chore(deps): Allow package resolution on all platforms ([6841d83])
- chore(deps): Lock file maintenance ([e0991b6])
- chore(deps): Update dependency twine to v7 ([0f06f5d])
- chore(lint): widen ruff scope to repo and enable PT rules ([7243514])
- perf(ci): split the CI build into lint, test and scan jobs ([e9b89e5])

### Fixed

- fix: batch op:// reference resolution ([b2a90f8])

### Removed

- ci: disable dependabot ([04b8024])

## [3000.5.0] - 2026-06-25

### Added

- feat: add log-safe `dsn_redacted()` helper to PostgresConfig ([85f0dca])

### Changed

- chore(ci): Update actions/checkout action to v7 ([d7ae1b7])
- chore: update python dependencies ([e9c5bfb])
- fix: default Postgres SSL mode to `require` instead of `prefer` ([91d626f])

### Fixed

- fix: resolve parameterized generic field annotations before issubclass ([ed2cc18])

## [3000.4.1] - 2026-06-16

### Changed

- chore(ci): Update SonarSource/sonarqube-scan-action action to v8.2.0 ([9e302e2])
- chore(ci): Update astral-sh/setup-uv action to v8.2.0 ([ed8b0aa])
- chore(deps): bump actions/checkout from 6.0.2 to 6.0.3 ([2aa9d2e])
- chore: update python dependencies ([5216dfc])
- fix(ci): expand DefectDojo auth header and fail the step on upload errors ([18f5bb9])

### Removed

- ci: remove skylos ([6026bdf])

## [3000.4.0] - 2026-03-24

### Added

- chore: add publish recipe ([03c114f])

### Changed

- chore: update .gitignore for IDE and agent directories ([d88b173])
- chore: update dependencies ([147834f])
- ci: add skylos workflow ([6269c0b])
- ci: harden zizmor config, add SHA pins ([76d4594])
- feat: allow onepassword-sdk-0.4 in dependencies ([01b9485])
- fix: include failed secret reference URI in resolution error message ([d5b1eda])
- fix: resolve Skylos quality and danger findings ([5bd3fb9])
- fix: update test fixture for onepassword-sdk 0.4 compatibility ([7880b48])

## [3000.3.0] - 2026-02-13

### Added

- chore: add build recipe ([4de6b3e])
- ci: add zizmor action ([e5a453a])

### Changed

- chore: format test files ([f723cf2])
- fix: sort out package renaming for good … ([973cbc0])
- fix: tweak setuptools config after rename ([579567d])

## [3000.2.2] - 2026-02-13

**Release retracted** due to a defect rendering it non-functional.

## [3000.2.1] - 2026-02-12

**Release retracted** due to a defect rendering it non-functional.

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

[Unreleased]: https://github.com/Utiligize/configator-op/compare/v3000.6.0...HEAD
[3000.6.0]: https://github.com/Utiligize/configator-op/compare/v3000.5.0...v3000.6.0
[3000.5.0]: https://github.com/Utiligize/configator-op/compare/v3000.4.1...v3000.5.0
[3000.4.1]: https://github.com/Utiligize/configator-op/compare/v3000.4.0...v3000.4.1
[3000.4.0]: https://github.com/Utiligize/configator-op/compare/v3000.3.0...v3000.4.0
[3000.3.0]: https://github.com/Utiligize/configator-op/compare/v3000.2.0...v3000.3.0
[3000.2.0]: https://github.com/Utiligize/configator-op/compare/v3000.1.1...v3000.2.0
[3000.1.1]: https://github.com/Utiligize/configator-op/compare/v3000.1.0...v3000.1.1
[3000.1.0]: https://github.com/Utiligize/configator-op/compare/v3000.0.2...v3000.1.0
[3000.0.2]: https://github.com/Utiligize/configator-op/compare/v3000.0.1...v3000.0.2
[3000.0.1]: https://github.com/Utiligize/configator-op/compare/v3000.0.0...v3000.0.1
[3000.0.0]: https://github.com/Utiligize/configator-op/releases/tag/v3000.0.0

<!-- only slugs below here -->
[01b9485]: https://github.com/Utiligize/configator-op/commit/01b9485654832e82861cc8c7a390cc190f38daf4
[03c114f]: https://github.com/Utiligize/configator-op/commit/03c114f08b5d0249bf2dfa4ad068871c43e89afb
[04b8024]: https://github.com/Utiligize/configator-op/commit/04b80240e580628ac7a7b6bdb72035cadf6c3d83
[0ddc16a]: https://github.com/Utiligize/configator-op/commit/0ddc16ac3e8e0637137bf93146630198215d6546
[0efeae6]: https://github.com/Utiligize/configator-op/commit/0efeae6f81e3dbecc5fcaea0afb9e564e6017331
[0f06f5d]: https://github.com/Utiligize/configator-op/commit/0f06f5dd44d54f23a0b76c9ae5d0412913de348b
[147834f]: https://github.com/Utiligize/configator-op/commit/147834f243868ecfe27152aad4251982b4755dbd
[15b1a43]: https://github.com/Utiligize/configator-op/commit/15b1a433c56a790715da5746d4beb50a7a1ca25d
[168fe4f]: https://github.com/Utiligize/configator-op/commit/168fe4f088df17c34782a14a07d9b8ef78b16f2d
[18f5bb9]: https://github.com/Utiligize/configator-op/commit/18f5bb9d1741cc91ffe88a56f9c0b4ea8e212972
[1be6eb3]: https://github.com/Utiligize/configator-op/commit/1be6eb35eae03f84a8251443c56d7753a4e41526
[2aa9d2e]: https://github.com/Utiligize/configator-op/commit/2aa9d2e884ba7e99ecdd6cf73ef10f2721340cb9
[2fbb13e]: https://github.com/Utiligize/configator-op/commit/2fbb13e9ab59dd72fce7f8d70cde51398d75f814
[387f552]: https://github.com/Utiligize/configator-op/commit/387f5525824ab4f6f2efde1d3b97c8758e3678d3
[397b932]: https://github.com/Utiligize/configator-op/commit/397b9329e21509d89d965807807b388b49da5dc0
[4de6b3e]: https://github.com/Utiligize/configator-op/commit/4de6b3e5bcc06d921f3c263dd692c5ecdf95762c
[50b4692]: https://github.com/Utiligize/configator-op/commit/50b469283ea63937d8993c8b70aa1a164f32b55f
[5216dfc]: https://github.com/Utiligize/configator-op/commit/5216dfc83b3b52cea84a62e7d62cfbe9c6e1b625
[579567d]: https://github.com/Utiligize/configator-op/commit/579567d6bd872896f25d8f0b8f9e2773407bcb59
[5bd3fb9]: https://github.com/Utiligize/configator-op/commit/5bd3fb9456d2bb37fc494cc6acb8d28349754709
[5ddbe83]: https://github.com/Utiligize/configator-op/commit/5ddbe839ddbb42fe72c1d5acffa2751ced5f967c
[5e63002]: https://github.com/Utiligize/configator-op/commit/5e6300203382896eed1b4b5a12c3fd51ce55453f
[6026bdf]: https://github.com/Utiligize/configator-op/commit/6026bdf39955a68efa803a9a28b8133ce458c68e
[6269c0b]: https://github.com/Utiligize/configator-op/commit/6269c0bbedd9819b672c0df25698e1544b23196e
[6841d83]: https://github.com/Utiligize/configator-op/commit/6841d83439f77b919c00ff385940e8104fb546d6
[6df3acd]: https://github.com/Utiligize/configator-op/commit/6df3acdef891c6b60b90ea96c128b317956b1671
[6e2571b]: https://github.com/Utiligize/configator-op/commit/6e2571bc009eb775d182c7a81493f9cf08ce8865
[7243514]: https://github.com/Utiligize/configator-op/commit/72435140f8fbc0d59f39516efe5290a2828db513
[7569cb8]: https://github.com/Utiligize/configator-op/commit/7569cb8540028800570513411a5ab5291ab45cc6
[76d4594]: https://github.com/Utiligize/configator-op/commit/76d459490bc57f3261ca5561b60dfb8768eb3c7c
[7844a80]: https://github.com/Utiligize/configator-op/commit/7844a80839d61114bd7578d36bdca8c50c14483a
[7880b48]: https://github.com/Utiligize/configator-op/commit/7880b4823ff164718a2bc86627af810ac00daf82
[7912d7f]: https://github.com/Utiligize/configator-op/commit/7912d7f109534dc8c114b4aa56c08fd1ac7a049e
[82c2a30]: https://github.com/Utiligize/configator-op/commit/82c2a30e95e185b41eb5c519243a16228b90e98a
[85f0dca]: https://github.com/Utiligize/configator-op/commit/85f0dca1f85a306ca792544483aeddccdc7cad61
[8d197e2]: https://github.com/Utiligize/configator-op/commit/8d197e2eb7183d4616e9cc214dcab4084bf75477
[91d626f]: https://github.com/Utiligize/configator-op/commit/91d626fb2d31c6d01df2a31af02c4d43972e10c2
[94d14ec]: https://github.com/Utiligize/configator-op/commit/94d14eccdec1257c717d4becae2b8e7f39a4add2
[9688a7c]: https://github.com/Utiligize/configator-op/commit/9688a7c1da90d13ce2d54bd270ab6a7e3f3e5de1
[973cbc0]: https://github.com/Utiligize/configator-op/commit/973cbc0a9a8b055c20a48c8992f15b7c7eed0fb6
[981fc8f]: https://github.com/Utiligize/configator-op/commit/981fc8f4087cef661888e93bf8d147a085f04dc6
[99405f2]: https://github.com/Utiligize/configator-op/commit/99405f2b6fd941be0db12201c4a44c0c065babcb
[9e302e2]: https://github.com/Utiligize/configator-op/commit/9e302e207124fdabdbbf3a358dcb971d9edf7e9c
[af8a42b]: https://github.com/Utiligize/configator-op/commit/af8a42bb59c2767724102d2a85d8f191ff53620d
[b2a90f8]: https://github.com/Utiligize/configator-op/commit/b2a90f8d6a87ee0aee70e38204866b011b6232fe
[bd2994a]: https://github.com/Utiligize/configator-op/commit/bd2994a26c44b0036d96ea0b1b28be0862a2597d
[d5b1eda]: https://github.com/Utiligize/configator-op/commit/d5b1eda3e53373bb3e69b46a3603ac1dff0f677c
[d7ae1b7]: https://github.com/Utiligize/configator-op/commit/d7ae1b778b7798f0cca0fa4aa3611008aaef6b29
[d88b173]: https://github.com/Utiligize/configator-op/commit/d88b173b1f7bb130b5d6e9a4c908328517562953
[e0991b6]: https://github.com/Utiligize/configator-op/commit/e0991b65e5508de5c94be1c340876fbd12fea414
[e5a453a]: https://github.com/Utiligize/configator-op/commit/e5a453ac59fe11fbea083b9168289ef111424dc4
[e9b89e5]: https://github.com/Utiligize/configator-op/commit/e9b89e5803473b165fd735b77fc75f71405e4ef5
[e9c5bfb]: https://github.com/Utiligize/configator-op/commit/e9c5bfb1d5182876354dd3974c97fd2e2bd10c3f
[ed2cc18]: https://github.com/Utiligize/configator-op/commit/ed2cc18f8e318db3e4bcd732d15141724ba9a5b3
[ed45385]: https://github.com/Utiligize/configator-op/commit/ed45385e514b42f2d0e86391cff416086e175ea4
[ed8b0aa]: https://github.com/Utiligize/configator-op/commit/ed8b0aa0a3bbc6fc0a731efa59f2ee4091672b77
[f18dfe9]: https://github.com/Utiligize/configator-op/commit/f18dfe9db79c03fe90cc27535b764e2b55af5942
[f723cf2]: https://github.com/Utiligize/configator-op/commit/f723cf265a17cbbede4d65ca9eb9c408b3b66940
[fccaa88]: https://github.com/Utiligize/configator-op/commit/fccaa88d0f869a204fcc0af0a0340b8cc1577dc7
