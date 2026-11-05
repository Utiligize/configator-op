from contextvars import Context
from os import getenv
from urllib.parse import parse_qs, urlsplit

import pytest
from pydantic import SecretStr, ValidationError
from structlog.testing import capture_logs

from configator.errors import ConfigInvalidError
from configator.models import PostgresConfig, SentryConfig


@pytest.fixture
def enable_dev_mode(monkeypatch):
    monkeypatch.setenv("CONFIGATOR_DEV_MODE", "SUDO MAKE ME A SANDWICH")


def _pg_cfg(sslmode: str):
    return PostgresConfig(
        PGHOST="localhost",
        PGPORT=5432,
        PGUSER="test_user",
        PGPASSWORD=SecretStr("hunter2"),
        PGDATABASE="test_db",
        PGSSLMODE=sslmode,
    )


@pytest.fixture
def pg_cfg_ssl_disabled():
    return _pg_cfg(sslmode="disable")


@pytest.fixture
def pg_cfg_ssl_required():
    return _pg_cfg(sslmode="require")


@pytest.fixture
def pg_env_cfg(monkeypatch):
    env_vars = {
        "PGHOST": "db.example.com",
        "PGPORT": "5433",
        "PGUSER": "env_user",
        "PGPASSWORD": "1234",
        "PGDATABASE": "env_db",
        "PGSSLMODE": "verify-ca",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)


def test_postgres_config_dsn_with_ssl(pg_cfg_ssl_required):
    """Test the DSN generation of PostgresConfig with forced SSL."""
    expected = "postgresql://test_user:hunter2@localhost:5432/test_db?sslmode=require"
    actual = f"{pg_cfg_ssl_required.dsn()}"
    assert actual == expected


def test_postgres_config_dsn_without_ssl(pg_cfg_ssl_disabled):
    """Test the DSN generation of PostgresConfig without SSL."""
    expected = "postgresql://test_user:hunter2@localhost:5432/test_db?sslmode=disable"
    actual = f"{pg_cfg_ssl_disabled.dsn()}"
    assert actual == expected


def test_postgres_config_dsn_redacted_masks_password(pg_cfg_ssl_required):
    """Test that dsn_redacted() does not expose the plaintext password."""
    redacted = f"{pg_cfg_ssl_required.dsn_redacted()}"
    assert "hunter2" not in redacted
    assert redacted == "postgresql://test_user:**********@localhost:5432/test_db?sslmode=require"


def test_postgres_config_defaults():
    """Test that the default values are set correctly in PostgresConfig with no env vals set."""
    default_config = PostgresConfig()
    expected = "postgresql://postgres:hunter2@localhost:5432/postgres?sslmode=require"
    actual = f"{default_config.dsn()}"
    assert actual == expected


def test_postgres_config_from_env(enable_dev_mode, pg_env_cfg):
    """Test that the values are set correctly in PostgresConfig with env vals set."""
    assert getenv("CONFIGATOR_DEV_MODE", None) is not None
    config = PostgresConfig(
        PGHOST="localhost",
        PGPORT=5432,
        PGUSER="postgres",
        PGPASSWORD=SecretStr("hunter2"),
        PGDATABASE="postgres",
        PGSSLMODE="prefer",
    )
    expected = "postgresql://env_user:1234@db.example.com:5433/env_db?sslmode=verify-ca"
    actual = f"{config.dsn()}"
    assert actual == expected


def test_postgres_config_from_env_only_when_dev_mode_enabled(pg_env_cfg):
    """Test that the values are *not* set from env when dev mode is not enabled."""
    assert getenv("CONFIGATOR_DEV_MODE", None) is None
    config = PostgresConfig(
        PGHOST="localhost",
        PGPORT=5432,
        PGUSER="postgres",
        PGPASSWORD=SecretStr("hunter2"),
        PGDATABASE="postgres",
        PGSSLMODE="prefer",
    )
    expected = "postgresql://postgres:hunter2@localhost:5432/postgres?sslmode=prefer"
    actual = f"{config.dsn()}"
    assert actual == expected


def test_postgres_config_sslmode_failed(monkeypatch):
    """Test that the sslmode is validated against the enum of allowed values."""
    with monkeypatch.context():
        monkeypatch.setenv("CONFIGATOR_DEV_MODE", "1")
        monkeypatch.setenv("PGSSLMODE", "cheese")
        with pytest.raises(ValidationError):
            _ = PostgresConfig()


def _pg_cfg_rootcert(rootcert: str) -> PostgresConfig:
    return PostgresConfig(
        PGUSER="test_user",
        PGDATABASE="test_db",
        PGSSLMODE="verify-full",
        PGSSLROOTCERT=rootcert,
    )


def _sslrootcert(dsn: object) -> str:
    """Return the decoded sslrootcert query value of a DSN."""
    values = parse_qs(urlsplit(str(dsn)).query)["sslrootcert"]
    assert len(values) == 1
    return values[0]


@pytest.fixture
def no_system_ca_bundle(monkeypatch, tmp_path):
    """Point every system CA bundle probe path at a file that does not exist."""
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    missing = tuple(tmp_path / f"missing-{i}.pem" for i in range(3))
    monkeypatch.setattr("configator.models._SYSTEM_CA_BUNDLES", missing)
    return missing


def test_postgres_config_dsn_without_rootcert_is_unchanged():
    """Test that an unset PGSSLROOTCERT leaves only sslmode in the query."""
    config = PostgresConfig(PGUSER="test_user", PGDATABASE="test_db", PGSSLMODE="verify-full")
    assert config.PGSSLROOTCERT is None
    expected = "postgresql://test_user:hunter2@localhost:5432/test_db?sslmode=verify-full"
    actual = str(config.dsn())
    assert actual == expected


def test_postgres_config_dsn_empty_rootcert_is_unset(monkeypatch):
    """Test that an empty PGSSLROOTCERT, e.g. from an env var, is treated as unset."""
    with monkeypatch.context():
        monkeypatch.setenv("CONFIGATOR_DEV_MODE", "1")
        monkeypatch.setenv("PGUSER", "test_user")
        monkeypatch.setenv("PGDATABASE", "test_db")
        monkeypatch.setenv("PGSSLMODE", "verify-full")
        monkeypatch.setenv("PGSSLROOTCERT", "")
        config = PostgresConfig(PGUSER="test_user", PGDATABASE="test_db", PGSSLMODE="verify-full")
        assert config.PGSSLROOTCERT == ""
        expected = "postgresql://test_user:hunter2@localhost:5432/test_db?sslmode=verify-full"
        actual = str(config.dsn())
        assert actual == expected


def test_postgres_config_dsn_rootcert_system_ignores_empty_ssl_cert_file(
    monkeypatch, no_system_ca_bundle, tmp_path
):
    """Test that `system` skips an empty SSL_CERT_FILE and probes the bundle paths."""
    bundle = tmp_path / "probed.pem"
    bundle.touch()
    monkeypatch.setenv("SSL_CERT_FILE", "")
    monkeypatch.setattr("configator.models._SYSTEM_CA_BUNDLES", (bundle,))
    config = _pg_cfg_rootcert("system")
    assert _sslrootcert(config.dsn()) == str(bundle)


def test_postgres_config_dsn_rootcert_path_is_url_encoded():
    """Test that an explicit path is URL-encoded, spaces as %20 rather than +."""
    config = _pg_cfg_rootcert("/opt/my certs/ca+root.pem")
    expected = (
        "postgresql://test_user:hunter2@localhost:5432/test_db"
        "?sslmode=verify-full&sslrootcert=/opt/my%20certs/ca%2Broot.pem"
    )
    actual = str(config.dsn())
    assert actual == expected


def test_postgres_config_dsn_rootcert_path_is_not_checked_for_existence(no_system_ca_bundle):
    """Test that an explicit path is passed through even if the file does not exist."""
    config = _pg_cfg_rootcert("/nonexistent/ca.pem")
    assert f"{config.dsn()}".endswith("&sslrootcert=/nonexistent/ca.pem")


def test_postgres_config_dsn_rootcert_system_uses_ssl_cert_file(monkeypatch, tmp_path):
    """Test that `system` resolves to SSL_CERT_FILE when it is set."""
    bundle = tmp_path / "bundle.pem"
    monkeypatch.setenv("SSL_CERT_FILE", str(bundle))
    config = _pg_cfg_rootcert("system")
    assert _sslrootcert(config.dsn()) == str(bundle)


def test_postgres_config_dsn_rootcert_system_picks_first_existing_probe(
    monkeypatch, no_system_ca_bundle, tmp_path
):
    """Test that `system` resolves to the first probe path that exists."""
    second = tmp_path / "second.pem"
    third = tmp_path / "third.pem"
    second.touch()
    third.touch()
    monkeypatch.setattr(
        "configator.models._SYSTEM_CA_BUNDLES", (no_system_ca_bundle[0], second, third)
    )
    config = _pg_cfg_rootcert("system")
    assert _sslrootcert(config.dsn()) == str(second)


def test_postgres_config_dsn_rootcert_system_not_found_raises(no_system_ca_bundle):
    """Test that `system` with no bundle found raises ConfigInvalidError naming the paths."""
    config = _pg_cfg_rootcert("system")
    with pytest.raises(ConfigInvalidError) as exc_info:
        config.dsn()
    message = str(exc_info.value)
    assert "SSL_CERT_FILE" in message
    for path in no_system_ca_bundle:
        assert str(path) in message


def test_postgres_config_dsn_redacted_carries_rootcert(monkeypatch, tmp_path):
    """Test that dsn_redacted() has the same sslrootcert as dsn(), with the password masked."""
    bundle = tmp_path / "bundle.pem"
    monkeypatch.setenv("SSL_CERT_FILE", str(bundle))
    config = _pg_cfg_rootcert("system")
    redacted = config.dsn_redacted()
    assert "hunter2" not in redacted
    assert redacted == f"{config.dsn()}".replace("hunter2", "**********")
    assert _sslrootcert(redacted) == str(bundle)


def test_sentry_env_prefix(monkeypatch):
    """Test that SentryConfig correctly uses the SENTRY_ env var prefix."""
    expected_dsn = "https://foo.invalid/123"
    with monkeypatch.context():
        monkeypatch.setenv("CONFIGATOR_DEV_MODE", "1")
        monkeypatch.setenv("SENTRY_DSN", expected_dsn)
        actual_dsn = SentryConfig(dsn="foo").dsn
        assert f"{actual_dsn}" == expected_dsn


@pytest.mark.parametrize("env_var", ["ENVIRONMENT", "APP_ENV"])
@pytest.mark.parametrize("env_value", ["product", "production", "PRODUCTION", "Production"])
def test_dev_mode_refused_in_production(monkeypatch, env_var, env_value):
    """Dev mode must refuse to activate when the environment resolves to production."""
    with monkeypatch.context():
        monkeypatch.setenv("CONFIGATOR_DEV_MODE", "1")
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.setenv(env_var, env_value)
        with pytest.raises(RuntimeError, match="CONFIGATOR_DEV_MODE"):
            _ = PostgresConfig()


def test_environment_prefers_environment_over_app_env(monkeypatch):
    """ENVIRONMENT takes precedence over APP_ENV when resolving the environment."""
    with monkeypatch.context():
        monkeypatch.setenv("CONFIGATOR_DEV_MODE", "1")
        monkeypatch.setenv("ENVIRONMENT", "develop")
        monkeypatch.setenv("APP_ENV", "product")
        _ = PostgresConfig()


def test_dev_mode_allowed_outside_production(monkeypatch):
    """Dev mode activates normally in non-production environments."""
    with monkeypatch.context():
        monkeypatch.setenv("CONFIGATOR_DEV_MODE", "1")
        monkeypatch.setenv("ENVIRONMENT", "staging")
        _ = PostgresConfig()


def test_dev_mode_logged_once_outside_load_config(monkeypatch):
    """Settings built directly log the developer mode once, not once per instance."""
    monkeypatch.setenv("CONFIGATOR_DEV_MODE", "1")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)

    def build_twice() -> list[str]:
        with capture_logs() as events:
            _ = PostgresConfig()
            _ = PostgresConfig()
        return [e["event"] for e in events]

    assert Context().run(build_twice) == ["configator developer mode is ENABLED"]
