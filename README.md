# ![Configator logo depicting a cool gator](configator.png)

<!-- markdownlint-disable MD036 -->
*A convenient way to load your app configuration from 1Password.*
<!-- markdownlint-enable MD036 -->

[![Ruff][ruff-badge-img]][ruff-badge-href]
[![CI status][github-actions-ci-badge-img]][github-actions-ci-badge-href]
[![Quality Gate Status][sonarcloud-quality-badge-img]][sonarcloud-badge-href]
[![Test Coverage][sonarcloud-cov-badge-img]][sonarcloud-badge-href]
[![Lines of Code][sonarcloud-loc-badge-img]][sonarcloud-badge-href]

This project is licensed under the terms of the MIT license.

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

> **⚠️ Never enable developer mode in production.** A stray `.env` file would
> silently override vetted secrets. Configator guards against this: if
> `CONFIGATOR_DEV_MODE` is set while `ENVIRONMENT` (or, as a fallback, `APP_ENV`)
> resolves to production — any value case-insensitively starting with `product`,
> e.g. `product` or `production` — instantiating a config model raises a
> `RuntimeError`. Production deployments must ensure `CONFIGATOR_DEV_MODE` is
> unset and that no `.env` file ships in production images.

This feature works with the provided common configuration models (`PostgresConfig`, `SentryConfig`). For your own config schemas, you can simply extend `ConfigatorSettings` to get this behavior.

## Installation

```bash
uv add "git+https://github.com/Utiligize/configator@v3000.0.0"
```

or, if you like the bleeding edge:

```bash
uv add "git+https://github.com/Utiligize/configator"
```

For information on how to authenticate uv with GitHub, see <https://docs.astral.sh/uv/concepts/authentication/git/>.

For information on how to use private repos in GitHub Actions, see <https://docs.astral.sh/uv/guides/integration/github/#private-repos>. If you create a fine-grained access token, it simply needs the "Content" read permission.

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
  All references in the config item are resolved together, one batched request per level of
  nesting, so a schema with many referencing fields costs a handful of 1Password requests
  rather than one per field. The request count for each load is emitted as an info log line.
- Every 1Password call is retried individually on transient failures (3 attempts, with no
  further attempt scheduled more than 10 seconds after the first), so a retry costs one
  request rather than a full reload. The cap bounds retrying, not a single hung request —
  the SDK exposes no request timeout. Rate-limit
  errors are never retried: they are logged and raised immediately, because the hourly read
  budget can be up to an hour from resetting and each retry would spend a request against a
  budget that is already empty.

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

## Error Handling

Every failure `load_config` reports about 1Password or the config item derives from `ConfigatorError`, so one `except` clause catches them all — the developer-mode production guard being the one deliberate exception, described at the end of this section. Below the base sit two types that answer the question a caller has to make a decision on — *is the config wrong, or is 1Password simply not answering?*

| Exception | Meaning | What a caller should do |
| --- | --- | --- |
| `ConfigUnavailableError` | 1Password could not be reached or would not answer: authentication failure, network or TLS error, rate limiting, an empty vault or item listing, or a reference that could not be resolved. | The config that is there may well be fine. A service that keeps a last-good config snapshot may boot from it rather than fail. |
| `ConfigInvalidError` | The item was read, but does not fit the schema: a field with no value and no default, a value that will not parse as its annotated type, malformed JSON in a collection field, a Pydantic validation failure, or a reference chain deeper than 10 links. | Fail loudly. Retrying and falling back to an older snapshot both serve stale config over a real, unfixed error; someone has to correct the 1Password item or the schema. |

An empty vault or item listing counts as *unavailable* rather than *invalid*, because a de-permissioned or rotated service-account token looks exactly like a vault that is not there.

Where a failure originates in an underlying exception — an SDK error, a parse failure, a Pydantic validation error — it is chained as `__cause__`, so the original message and traceback survive. Failures Configator detects itself have no `__cause__`: a vault or item absent from a listing, a required field with no value, a reference the response omits, and the depth guard all raise on their own. Treat `__cause__` as optional:

```python
from configator import ConfigInvalidError, ConfigUnavailableError, load_config

try:
    cfg = await load_config(schema=Config, token=token, vault=vault, item=item)
except ConfigUnavailableError as exc:
    log.warning("1Password unavailable, booting from snapshot: %s", exc.__cause__ or exc)
    cfg = load_snapshot()
except ConfigInvalidError:
    log.exception("config item does not fit the schema")
    raise
```

The developer-mode production guard described above is deliberately not part of this hierarchy: it still raises a plain `RuntimeError`, because it is a refusal to start rather than a report about the config item.

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
