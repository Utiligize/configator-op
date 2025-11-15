# ![Configator logo depicting a cool gator](configator.png)

<!-- markdownlint-disable MD036 -->
*A convenient way to load your app configuration from 1Password*
<!-- markdownlint-enable MD036 -->

## Features

- 🔐 **Secure**: Load configuration from 1Password vaults
- 📦 **Type-safe**: Pydantic models for typed configuration
- 🔄 **Recursive**: Automatically resolves `op://` secret references

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
- Any string starting with `op://` will be resolved recursively (up to a depth of 10 links).

### Planned Features

- Collections (`list`, `tuple`, `set`, `dict`) are yet to be implemented.
- Providing access to extra fields in the config item when `model_config = ConfigDict(extra='allow')` is specified in the input model. See <https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.extra>.

### Unsupported Features

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
