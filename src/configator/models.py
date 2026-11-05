"""Common models that can be used as mixins or base config classes."""

###################################################################################################
# Copyright (c) 2025-2026 Utiligize ApS <contact@utiligize.com>                                   #
# This file is part of Configator: <https://github.com/Utiligize/configator>                      #
# SPDX-License-Identifier: MIT                                                                    #
# License-Filename: LICENSE.md                                                                    #
###################################################################################################

from enum import StrEnum, unique
from os import getenv
from pathlib import Path
from urllib.parse import quote, urlencode

from pydantic import Field, HttpUrl, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from .environment import Environment as Environment
from .environment import dev_mode_enabled, log_dev_mode_once, refuse_dev_mode_in_production
from .errors import ConfigInvalidError


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
        refuse_dev_mode_in_production()
        log_dev_mode_once()
        if dev_mode_enabled():
            return dotenv_settings, env_settings, init_settings, file_secret_settings
        else:
            return init_settings, env_settings, dotenv_settings, file_secret_settings


@unique
class _PostgresSSLMode(StrEnum):
    DISABLE = "disable"
    ALLOW = "allow"
    PREFER = "prefer"
    REQUIRE = "require"
    VERIFY_CA = "verify-ca"
    VERIFY_FULL = "verify-full"


# Probed in order when PGSSLROOTCERT is "system" and SSL_CERT_FILE is unset.
# ssl.get_default_verify_paths() is no help: its cafile is None on uv's
# python-build-standalone interpreters.
_SYSTEM_CA_BUNDLES: tuple[Path, ...] = (
    Path("/etc/ssl/certs/ca-certificates.crt"),  # Debian, Ubuntu
    Path("/etc/pki/tls/certs/ca-bundle.crt"),  # RHEL
    Path("/etc/ssl/cert.pem"),  # Alpine, macOS
)


def _system_ca_bundle() -> str:
    """Return the path of the OS CA bundle, for ``sslrootcert=system``.

    asyncpg reads ``sslrootcert`` from the DSN but, unlike libpq 16+, takes
    ``system`` as a file name, so Configator resolves it to a real path.
    """
    if cert_file := getenv("SSL_CERT_FILE"):
        return cert_file
    for bundle in _SYSTEM_CA_BUNDLES:
        if bundle.is_file():
            return str(bundle)
    tried = ", ".join(str(bundle) for bundle in _SYSTEM_CA_BUNDLES)
    raise ConfigInvalidError(
        f"PGSSLROOTCERT is 'system' but no OS CA bundle was found; "
        f"SSL_CERT_FILE is unset and none of these exist: {tried}"
    )


class PostgresConfig(ConfigatorSettings):
    """PostgreSQL configuration schema."""

    PGHOST: str = "localhost"
    PGPORT: int = 5432
    PGUSER: str = "postgres"
    PGPASSWORD: SecretStr = SecretStr("hunter2")
    PGDATABASE: str = "postgres"
    PGSSLMODE: _PostgresSSLMode = _PostgresSSLMode("require")
    PGSSLROOTCERT: str | None = None
    SCHEME: str = "postgresql"

    def _query(self) -> str:
        """Build the DSN query string shared by ``dsn()`` and ``dsn_redacted()``."""
        params = {"sslmode": str(self.PGSSLMODE)}
        if self.PGSSLROOTCERT:
            rootcert = self.PGSSLROOTCERT
            if rootcert == "system":
                rootcert = _system_ca_bundle()
            params["sslrootcert"] = rootcert
        return urlencode(params, safe="/", quote_via=quote)

    def dsn(self) -> PostgresDsn:
        """Build the PostgreSQL DSN string.

        WARNING: the returned DSN embeds the plaintext password and must never
        be logged, included in an exception, or sent to error-reporting tools.
        Use ``dsn_redacted()`` for any logging or diagnostic output.

        Raises ``ConfigInvalidError`` when ``PGSSLROOTCERT`` is ``system`` and
        no OS CA bundle is found.
        """
        return PostgresDsn.build(
            scheme=self.SCHEME,
            username=self.PGUSER,
            password=self.PGPASSWORD.get_secret_value(),
            host=self.PGHOST,
            port=self.PGPORT,
            path=f"{self.PGDATABASE}",
            query=self._query(),
        )

    def dsn_redacted(self) -> str:
        """Build a log-safe PostgreSQL DSN string with the password masked.

        Safe to log or include in diagnostics; use this instead of ``dsn()``
        anywhere the value may be persisted or transmitted. Returns a plain
        ``str`` because the masked password makes it unusable as a real DSN.

        Raises ``ConfigInvalidError`` when ``PGSSLROOTCERT`` is ``system`` and
        no OS CA bundle is found.
        """
        return str(
            PostgresDsn.build(
                scheme=self.SCHEME,
                username=self.PGUSER,
                password=str(self.PGPASSWORD),
                host=self.PGHOST,
                port=self.PGPORT,
                path=f"{self.PGDATABASE}",
                query=self._query(),
            )
        )


class SentryConfig(ConfigatorSettings):
    """Sentry configuration schema."""

    model_config = SettingsConfigDict(env_prefix="SENTRY_")

    dsn: HttpUrl
    enabled: bool = True
    send_default_pii: bool = False
    traces_sample_rate: float = Field(default=0.0, ge=0.0, le=1.0)
