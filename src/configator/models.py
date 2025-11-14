"""Common models that can be used as mixins or base config classes."""

from enum import StrEnum, unique
from os import getenv

from pydantic import BaseModel, ConfigDict, Field, PostgresDsn, SecretStr
from structlog import get_logger

log = get_logger()


@unique
class Environment(StrEnum):
    DEVELOPMENT = "develop"
    STAGING = "staging"
    PRODUCTION = "product"


@unique
class PostgresSSLMode(StrEnum):
    DISABLE = "disable"
    ALLOW = "allow"
    PREFER = "prefer"
    REQUIRE = "require"
    VERIFY_CA = "verify-ca"
    VERIFY_FULL = "verify-full"

    @classmethod
    def from_env(cls) -> "PostgresSSLMode":
        """Create PostgresSSLMode based on environment variable PGSSLMODE."""
        env_val = getenv("PGSSLMODE", "prefer")
        try:
            self = cls(env_val)
        except ValueError:
            log.warning(f"invalid SSL mode, falling back to `prefer`: PGSSLMODE={env_val}")
            self = cls("prefer")
        return self


class PostgresConfig(BaseModel):
    """PostgreSQL configuration schema."""

    model_config = ConfigDict(use_enum_values=True)

    host: str = getenv("PGHOST", "localhost")
    port: int = int(getenv("PGPORT", 5432))
    user: str = getenv("PGUSER", "postgres")
    password: SecretStr = SecretStr(getenv("PGPASSWORD", "hunter2"))
    database: str = getenv("PGDATABASE", "postgres")
    sslmode: PostgresSSLMode = PostgresSSLMode.from_env()

    def dsn(self) -> PostgresDsn:
        """Get the PostgreSQL DSN string."""
        return PostgresDsn(
            f"postgresql://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.database}?sslmode={self.sslmode}"
        )


class SentryConfig(BaseModel):
    """Sentry configuration schema."""

    dsn: SecretStr
    send_default_pii: bool = False
    traces_sample_rate: float = Field(default=0.0, ge=0.0, le=1.0)
