# ![Configator logo depicting a cool gator](configator.png)

<!-- markdownlint-disable MD036 -->
*A convenient way to load your app configuration from 1Password*
<!-- markdownlint-enable MD036 -->

[![Ruff][ruff-badge-img]][ruff-badge-href]
[![CI status][github-actions-ci-badge-img]][github-actions-ci-badge-href]
[![Quality Gate Status][sonarcloud-quality-badge-img]][sonarcloud-badge-href]
[![Test Coverage][sonarcloud-cov-badge-img]][sonarcloud-badge-href]
[![Lines of Code][sonarcloud-loc-badge-img]][sonarcloud-badge-href]

## Quick Start

```python
import asyncio
import os
from configator import load_config
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    host: str
    port: int
    username: str
    password: str

class AppConfig(BaseModel):
    api_key: str
    debug: bool
    timeout: int

class Config(BaseModel):
    db: DatabaseConfig
    app: AppConfig
    debug: bool = False

async def main():
    token = os.getenv("OP_SERVICE_ACCOUNT_TOKEN")
    cfg: Config = await load_config(
        schema=Config,
        token=token,
        vault="REPO whatever",
        item="whatever-develop",
    )
    assert cfg.db.port == 5432

asyncio.run(main())
```

### Developer Mode

For local development, you can override configuration values using a `.env` file by setting the `CONFIGATOR_DEV_MODE` environment variable:

```bash
export CONFIGATOR_DEV_MODE=1
```

When developer mode is enabled, values are loaded with the following priority (highest to lowest):

1. `.env` file
2. Environment variables
3. 1Password values (via initialization parameters)

Without developer mode, the standard priority applies (1Password values take precedence over environment variables and .env files).

This feature works with the provided common configuration models (`PostgresConfig`, `SentryConfig`). For your own config schemas, you can simply extend `ConfigatorSettings` to get this behavior.

## Installation

```bash
uv pip install "git+https://github.com/Utiligize/configator@v3000"
```

or, if you like the bleeding edge:

```bash
uv pip install "git+https://github.com/Utiligize/configator"
```

For information on how to authenticate uv with GitHub, see <https://docs.astral.sh/uv/concepts/authentication/git/>.

For information on how to use private repos in GitHub Actions, see <https://docs.astral.sh/uv/guides/integration/github/#private-repos>

## Writing Config Classes

Define your app's config as a class deriving from Pydantic's `BaseModel`. The field names will be matched against the 1Password item field titles, and the values loaded from them. The field names are treated as lower snake case, and item field names in 1Password are converted accordingly when matching. For example, a Python model with a field called `sentry_key` will match a 1Password item with a field title of `SENTRY_KEY` or `sentry-key`. It is therefore important to ensure that field names are unique, at least within sections.

Nested models are loaded from separate sections in the 1Password item. Fields in these nested models can have the same name as fields in other sections. Fields in the base config class are found by name, no matter their section (but the intention is for them to be added without one), so the names of these must be unique in the full model.

### Supported Features

- Basic types (`str`, `int`, `float`, even `complex`) are simply parsed from the string in 1Password.
- `decimal.Decimal` is also supported and should usually be preferred over `float`.
- Booleans are special: since any string is truthy in Python, a `bool` must have one of 8 (case-insensitive) values:
  - "true", "1", "yes", and "on" are interpreted as `True`.
  - "false", "0", "no", and "off" are interpreted as `False`.
  - any other value for a field defined as `bool` will raise a `ValueError`.
- Collections (`dict`, `list`, `set`) are loaded by interpreting the string value in 1Password as JSON and passing that object to the constructor. This means that a set can be constructed from what looks like a list, for example.
- Any string starting with `op://` will be resolved recursively (up to a depth of 10 links).

### Planned Features

- Providing access to extra fields in the config item when `model_config = ConfigDict(extra='allow')` is specified in the input model. See <https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.extra>.

### Unsupported Features

- Typed collections are sadly not supported, because it confuses the `issubclass` matching of fields. This means that fields in your config model must be defined as e.g. plain `dict`, not `dict[str, str]`.
- `Optional` and `Union` fields are **not** supported, i.e. you cannot do either of

  ```python
  foo: str | None = None
  bar: Optional[str]
  baz: int | float
  ```

  because it confuses the hydrator, who won't know which constructor to call or will try to initialize `None`.
- While `default` values are supported, `default_factory` is not.
- Basic Python types `bytes` and `bytearray` may work but are not officially supported.
- Arbitrary JSON is not supported, but you may be able to `loads` it from a string. Caveat emptor.

## Development

### Setup

```plain
uv sync
```

### Lint and Format

```plain
just lint
```

### Run Tests

```plain
just test
```

### Run Failed Tests

```plain
just test-failed
```

◼️◼️◼️

[github-actions-ci-badge-href]: https://github.com/Utiligize/configator/actions/workflows/ci.yml
[github-actions-ci-badge-img]: https://github.com/Utiligize/configator/actions/workflows/ci.yml/badge.svg?branch=main
[ruff-badge-href]: https://github.com/astral-sh/ruff
[ruff-badge-img]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
[sonarcloud-badge-href]: https://sonarcloud.io/summary/new_code?id=utiligize%3Aconfigator
[sonarcloud-cov-badge-img]: https://sonarcloud.io/api/project_badges/measure?project=utiligize%3Aconfigator&metric=coverage&token=f897eae3def4fd2e7e3bc7bd5a302da020955100
[sonarcloud-loc-badge-img]: https://sonarcloud.io/api/project_badges/measure?project=utiligize%3Aconfigator&metric=ncloc&token=f897eae3def4fd2e7e3bc7bd5a302da020955100
[sonarcloud-quality-badge-img]: https://sonarcloud.io/api/project_badges/measure?project=utiligize%3Aconfigator&metric=alert_status&token=f897eae3def4fd2e7e3bc7bd5a302da020955100
