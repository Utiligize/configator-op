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

# Publish to PyPI, then tag the release and create it on GitHub
release: release-check publish
  #!/usr/bin/env bash
  set -euo pipefail
  version=$(uv version --short)
  git tag --annotate "v${version}" --message "v${version}"
  git push origin "v${version}"
  {{quote(just_executable())}} --justfile {{quote(justfile())}} release-notes "${version}" \
    | gh release create "v${version}" --verify-tag --title "v${version}" --notes-file -

# Check that the current version is ready to be released
release-check:
  #!/usr/bin/env bash
  set -euo pipefail
  fail() { echo "release-check: $*" >&2; exit 1; }
  version=$(uv version --short)
  [ "$(git branch --show-current)" = main ] || fail "not on main"
  git fetch --quiet --tags origin main
  [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || fail "main is not in sync with origin/main"
  if git rev-parse --quiet --verify "refs/tags/v${version}" >/dev/null; then
    fail "tag v${version} already exists"
  fi
  gh auth status >/dev/null 2>&1 || fail "gh is not authenticated"
  {{quote(just_executable())}} --justfile {{quote(justfile())}} release-notes "${version}" >/dev/null

# Print a version's CHANGELOG section as GitHub release notes
release-notes version=`uv version --short`:
  #!/usr/bin/env bash
  set -euo pipefail
  awk -v version={{quote(version)}} '
    index($0, "## [" version "]") == 1 { in_section = 1; next }
    in_section && /^(## \[|<!--)/ { in_section = 0 }
    in_section { sub(/ \(\[[0-9a-f]+\](, \[[0-9a-f]+\])*\)$/, ""); lines[++n] = $0 }
    index($0, "[" version "]: ") == 1 { link = substr($0, length(version) + 5) }
    END {
      if (n == 0 || link == "") {
        print "release-notes: no CHANGELOG section or compare link for " version > "/dev/stderr"
        exit 1
      }
      first = 1; while (first <= n && lines[first] == "") first++
      last = n; while (last >= first && lines[last] == "") last--
      for (i = first; i <= last; i++) print lines[i]
      printf "\n**Full Changelog**: %s\n", link
    }
  ' {{quote(justfile_directory() / "CHANGELOG.md")}}

# Sync dependencies
sync:
  uv sync

# Run test suite
test: sync
  uv run -m pytest

# Rerun failed tests
test-failed: sync
  uv run -m pytest --last-failed
