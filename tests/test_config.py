import pytest
from pydantic import ValidationError

from app.config import Settings

ENV_KEYS = ("DATABASE_URL", "POSTGRES", "ADMIN_PASSWORD", "DEV_MODE", "CORS_ORIGINS")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def make(**env) -> Settings:
    return Settings(_env_file=None, **env)


def test_database_url_has_priority_over_legacy_postgres(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@local:5433/dev")
    monkeypatch.setenv("POSTGRES", "postgresql://u:p@remote:2001/prod")
    assert make().get_database_url() == "postgresql://u:p@local:5433/dev"


def test_legacy_postgres_used_only_when_database_url_not_set(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("POSTGRES", "'postgres://u:p@remote:2001/prod'")
    assert make().get_database_url() == "postgresql://u:p@remote:2001/prod"


def test_admin_password_required_outside_dev_mode():
    with pytest.raises(ValidationError):
        make(DEV_MODE=False)


def test_admin_password_defaults_in_dev_mode_and_explicit_wins():
    assert make(DEV_MODE=True).ADMIN_PASSWORD == "admin-dev"
    assert make(DEV_MODE=False, ADMIN_PASSWORD="s3cret").ADMIN_PASSWORD == "s3cret"


def test_cors_origins_parsed_from_comma_separated_list():
    s = make(DEV_MODE=True, CORS_ORIGINS="https://a.com, https://b.com ,")
    assert s.cors_origins_list == ["https://a.com", "https://b.com"]
    assert "*" not in make(DEV_MODE=True).cors_origins_list
