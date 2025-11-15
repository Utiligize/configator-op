from os import getenv

from pydantic import SecretStr, ValidationError
from pytest import fixture, raises

from configator.models import PostgresConfig, SentryConfig


@fixture
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

@fixture
def pg_cfg_ssl_disabled():
    return _pg_cfg(sslmode="disable")

@fixture
def pg_cfg_ssl_required():
    return _pg_cfg(sslmode="require")

@fixture
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

def test_postgres_config_defaults():
    """Test that the default values are set correctly in PostgresConfig with no env vals set."""
    default_config = PostgresConfig()
    expected = "postgresql://postgres:hunter2@localhost:5432/postgres?sslmode=prefer"
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
        with raises(ValidationError):
            _ = PostgresConfig()

def test_sentry_env_prefix(monkeypatch):
    """Test that SentryConfig correctly uses the SENTRY_ env var prefix."""
    expected_dsn = "https://foo.invalid/123"
    with monkeypatch.context():
        monkeypatch.setenv("CONFIGATOR_DEV_MODE", "1")
        monkeypatch.setenv("SENTRY_DSN", expected_dsn)
        actual_dsn = SentryConfig(dsn="foo").dsn
        assert f"{actual_dsn}" == expected_dsn
