"""Common models that can be used as mixins or base config classes."""

###################################################################################################
# Copyright (c) 2025 Utiligize ApS <contact@utiligize.com>                                        #
# This file is part of Configator: <https://github.com/Utiligize/configator>                      #
# SPDX-License-Identifier: MIT                                                                    #
# License-Filename: LICENSE.md                                                                    #
###################################################################################################

from enum import StrEnum, unique
from os import getenv

from pydantic import Field, HttpUrl, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from .log import get_logger

log = get_logger()


class ConfigatorSettings(BaseSettings):
    """Base configuration schema for Configator.

    If "developer mode" is activated by setting the environment value
    `CONFIGATOR_DEV_MODE` to a non-empty value, prefer loading values
    from .env file first, then from environment variables, then from
    init kwargs. Otherwise, keep normal loading priority.

    To learn more about what is going on here, read
    <https://docs.pydantic.dev/latest/concepts/pydantic_settings/#customise-settings-sources>
    """

    model_config = SettingsConfigDict(use_enum_values=True)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        dev_mode = getenv("CONFIGATOR_DEV_MODE", None)
        log_msg = "configator developer mode is %s"
        if dev_mode:
            log.warning(log_msg, "ENABLED")
            return dotenv_settings, env_settings, init_settings, file_secret_settings
        else:
            log.debug(log_msg, "disabled")
            return init_settings, env_settings, dotenv_settings, file_secret_settings


@unique
class Environment(StrEnum):
    DEVELOPMENT = "develop"
    STAGING = "staging"
    PRODUCTION = "product"


@unique
class _PostgresSSLMode(StrEnum):
    DISABLE = "disable"
    ALLOW = "allow"
    PREFER = "prefer"
    REQUIRE = "require"
    VERIFY_CA = "verify-ca"
    VERIFY_FULL = "verify-full"


class PostgresConfig(ConfigatorSettings):
    """PostgreSQL configuration schema."""

    PGHOST: str = "localhost"
    PGPORT: int = 5432
    PGUSER: str = "postgres"
    PGPASSWORD: SecretStr = SecretStr("hunter2")
    PGDATABASE: str = "postgres"
    PGSSLMODE: _PostgresSSLMode = _PostgresSSLMode("prefer")
    SCHEME: str = "postgresql"

    def dsn(self) -> PostgresDsn:
        """Build the PostgreSQL DSN string."""
        return PostgresDsn.build(
            scheme=self.SCHEME,
            username=self.PGUSER,
            password=self.PGPASSWORD.get_secret_value(),
            host=self.PGHOST,
            port=self.PGPORT,
            path=f"{self.PGDATABASE}",
            query=f"sslmode={self.PGSSLMODE}",
        )


class SentryConfig(ConfigatorSettings):
    """Sentry configuration schema."""

    model_config = SettingsConfigDict(env_prefix="SENTRY_")

    dsn: HttpUrl
    enabled: bool = True
    send_default_pii: bool = False
    traces_sample_rate: float = Field(default=0.0, ge=0.0, le=1.0)
