set dotenv-load

# Print this list
@default:
  just --list
  echo
  echo To add completions in bash, do:
  echo '$ source <(just --completions bash)'
  echo

# Build wheels
build: is-clean
  uv build

# Check whether the repo is clean
is-clean:
  @[ -z "$(git status --porcelain)" ]

# Lint the project
lint:
  uv run python -m ruff format {{justfile_directory()}}/src
  uv run python -m ruff check {{justfile_directory()}}/src
  cd {{justfile_directory()}}/src && uv run python -m mypy -p configator --config-file {{justfile_directory()}}/pyproject.toml

# Lint the project for the CI pipeline
lint-ci:
  #!/usr/bin/env bash
  EXIT_STATUS=0
  uv run python -m ruff format --check {{justfile_directory()}}/src || EXIT_STATUS=$?
  uv run python -m ruff check {{justfile_directory()}}/src || EXIT_STATUS=$?
  cd {{justfile_directory()}}/src && uv run python -m mypy -p configator --config-file {{justfile_directory()}}/pyproject.toml || EXIT_STATUS=$?
  exit $EXIT_STATUS

# Let Ruff auto-fix what it can
lint-fix:
  uv run python -m ruff check --fix {{justfile_directory()}}/src

# Sync dependencies
sync:
  uv sync

# Run test suite
test: sync
  uv run -m pytest

# Rerun failed tests
test-failed: sync
  uv run -m pytest --last-failed
