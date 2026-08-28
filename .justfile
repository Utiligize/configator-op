set dotenv-load

# Print this list
@default:
  just --list
  echo
  echo To add completions in bash, do:
  echo '$ source <(just --completions bash)'
  echo

# Build wheels
build: is-clean clean-dist
  uv build

# Remove build artifacts
clean-dist:
  rm -rf {{quote(justfile_directory() / "dist")}}

# Check whether the repo is clean
is-clean:
  @[ -z "$(git status --porcelain)" ]

# Lint the project
lint:
  uv run python -m ruff format {{quote(justfile_directory())}}
  uv run python -m ruff check {{quote(justfile_directory())}}
  cd {{quote(justfile_directory())}} && uv run pyrefly check --min-severity warn

# Lint the project for the CI pipeline
lint-ci:
  #!/usr/bin/env bash
  EXIT_STATUS=0
  uv run python -m ruff format --check {{quote(justfile_directory())}} || EXIT_STATUS=$?
  uv run python -m ruff check {{quote(justfile_directory())}} || EXIT_STATUS=$?
  cd {{quote(justfile_directory())}} && uv run pyrefly check --min-severity warn || EXIT_STATUS=$?
  exit $EXIT_STATUS

# Let Ruff auto-fix what it can
lint-fix:
  uv run python -m ruff check --fix {{quote(justfile_directory())}}

# Publish built package to PyPI
publish: build
  uv run twine upload {{quote(justfile_directory() / "dist")}}/*

# Sync dependencies
sync:
  uv sync

# Run test suite
test: sync
  uv run -m pytest

# Rerun failed tests
test-failed: sync
  uv run -m pytest --last-failed
