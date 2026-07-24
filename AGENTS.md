# AGENTS.md

This file provides guidance to AI agents working with code in this repository.

## Architecture Decision Records

Architecture decisions are documented in `ADRs.md` in the repository root. All code must adhere to the decisions recorded there.

## Changelog

The project keeps a changelog in `CHANGELOG.md`. Usage is as described at <https://keepachangelog.com/en/1.1.0/>.

## SDK Docs

The module is built around the 1Password SDK which has docs at <https://developer.1password.com/docs/sdks/>.

## Commands

- **Lint, format and type check:** `just lint`
- **Test:** `just test` or for single test: `uv run python -m pytest tests/path/to/test.py::test_function`
- **Test Failed:** `just test-failed`

## Code Style Guidelines

- Python version: 3.12 (strict)
- Line length: 99 characters
- Indentation: 4 spaces for Python files
- Imports: Grouped by stdlib, third-party, local with alphabetical ordering
- Type hints: Required for all functions in `src/` (enforced by Ruff's `ANN` rules); type checking via Pyrefly
- Naming: Follow Python conventions (snake_case for functions/variables, CamelCase for classes)
- Docstrings: Follow PEP 257 for concise, single-line docstrings for simple functions, more detailed for complex functionality
- Testing: Use pytest fixtures and appropriate mocking
- Formatting: Enforced by Ruff with rules listed in `pyproject.toml`
- Git commit messages: Use the Conventional Commits style
- When importing Python packages, use the explicit style `from <package> import <method>`

## MCP Tools & Configuration

- **Context7:** Use for up-to-date documentation for third-party code libraries
- **SonarQube:** See `sonar-project.properties` for project setup

## Implementation Workflow

This repository follows **GitHub Flow** for version control and collaboration.

### Adding Dependencies

To add a new dependency:

1. Add it to the `dependencies` list in `pyproject.toml`
2. Run `uv sync` to install and lock the dependency
3. For development-only dependencies, add to `dev-dependencies` in `[tool.uv]` section

### Tools

- Use `fd` <https://github.com/sharkdp/fd> instead of classic `find`.
- Use `rg` <https://github.com/BurntSushi/ripgrep> instead of classic `grep`.

### Testing

- Practise TDD: first write a failing test, then implement the code
- Test files go in `tests/` directory
- S101 (assert usage) is allowed in tests
- Coverage enabled with branch coverage
- Use pytest fixtures and standard pytest patterns

### Branch Strategy

- **main**: Production-ready code, protected branch
- **feature branches**: Created from main for all changes

### Development Process

1. **Create feature branch from main**:

   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```

2. **Make changes and commit** with conventional commits:

   ```bash
   git add .
   git commit -m "feat: add new feature …"
   ```

3. **Push branch and create Pull Request**:

   ```bash
   git push origin feature/your-feature-name
   ```

4. **Code review and automated tests run**:
   - CI/CD runs automated checks (linting, tests, builds)
   - At least one approval required from code owner
   - All automated checks must pass

5. **Merge to main after approval**:
   - Squash and merge recommended for clean history

### Pull Request Requirements

**IMPORTANT**: When creating a pull request, GitHub will automatically populate the PR description with a template from `.github/pull_request_template.md`. Please fill out all sections:

- **Description of PR**: Brief description of changes
- **Link to Jira ticket**: Reference to UT-XXXX ticket
- **How to verify**: Steps to verify the changes work
- **Testing**: Describe testing approach (CI pipeline, manual, etc.)

Additionally:

- **Passing CI/CD checks**: All tests, lints, and builds pass
- **At least one approval**: From designated code owner
- **Up-to-date with main branch**: Resolve conflicts before merge

### Branch Protection Rules

- **main branch**: Protected, requires PR, 1+ approval, passing checks
- Direct commits to main are prohibited
- Force pushes are disabled
