from pydantic import SecretStr

from configator.models import PostgresConfig

_pwd = SecretStr("hunter2")

def test_postgres_config_dsn_with_ssl():
    """Test the DSN generation of PostgresConfig with forced SSL."""
    config = PostgresConfig(
        host="localhost",
        port=5432,
        user="test_user",
        password=_pwd,
        database="test_db",
        sslmode="require",
    )
    expected = "postgresql://test_user:hunter2@localhost:5432/test_db?sslmode=require"
    actual = f"{config.dsn()}"
    assert actual == expected

def test_postgres_config_dsn_without_ssl():
    """Test the DSN generation of PostgresConfig without SSL."""
    config = PostgresConfig(
        host="localhost",
        port=5432,
        user="test_user",
        password=_pwd,
        database="test_db",
        sslmode="disable",
    )
    expected = "postgresql://test_user:hunter2@localhost:5432/test_db?sslmode=disable"
    actual = f"{config.dsn()}"
    assert actual == expected

def test_postgres_config_defaults():
    """Test that the default values are set correctly in PostgresConfig with no env vals set."""
    default_config = PostgresConfig()
    expected = "postgresql://postgres:hunter2@localhost:5432/postgres?sslmode=prefer"
    actual = f"{default_config.dsn()}"
    assert actual == expected

def test_postgres_config_defaults_from_env(monkeypatch):
    """Test that the default values are set correctly in PostgresConfig with env vals set."""
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
    config = PostgresConfig()
    expected = "postgresql://env_user:1234@db.example.com:5433/env_db?sslmode=verify-ca"
    actual = f"{config.dsn()}"
    assert actual == expected

def test_postgres_config_sslmode_fallback(monkeypatch):
    """Test that the default sslmode is set to `prefer` if a wrong value is set in the env."""
    monkeypatch.setenv("PGSSLMODE", "cheese")
    config = PostgresConfig()
    expected = "postgresql://postgres:hunter2@localhost:5432/postgres?sslmode=prefer"
    actual = f"{config.dsn()}"
    assert actual == expected
