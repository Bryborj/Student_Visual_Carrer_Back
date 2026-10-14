import pytest
from pydantic import ValidationError

from app.config import Settings

ENV_KEYS = ("DATABASE_URL", "POSTGRES", "ADMIN_PASSWORD", "DEV_MODE", "CORS_ORIGINS", "JWT_SECRET")


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


def test_admin_password_and_jwt_secret_required_outside_dev_mode():
    with pytest.raises(ValidationError) as exc:
        make(DEV_MODE=False)
    assert "ADMIN_PASSWORD" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        make(DEV_MODE=False, ADMIN_PASSWORD="admin")
    assert "JWT_SECRET" in str(exc.value)


def test_admin_password_and_jwt_secret_defaults_in_dev_mode_and_explicit_wins():
    dev_settings = make(DEV_MODE=True)
    assert dev_settings.ADMIN_PASSWORD == "admin-dev"
    assert "dev-jwt" in dev_settings.JWT_SECRET

    prod_settings = make(DEV_MODE=False, ADMIN_PASSWORD="s3cret", JWT_SECRET="jwt-prod-secret")
    assert prod_settings.ADMIN_PASSWORD == "s3cret"
    assert prod_settings.JWT_SECRET == "jwt-prod-secret"


def test_cors_origins_parsed_from_comma_separated_list():
    s = make(DEV_MODE=True, CORS_ORIGINS="https://a.com, https://b.com ,")
    assert s.cors_origins_list == ["https://a.com", "https://b.com"]
    assert "*" not in make(DEV_MODE=True).cors_origins_list
