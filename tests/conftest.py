"""Fixtures compartidas. Los tests con BD usan un Postgres REAL (docker compose / servicio CI).

Seguridad: se usa siempre una base de datos cuyo nombre termina en ``_test`` para no tocar datos de desarrollo.
"""
import os
from urllib.parse import urlparse

# --- Entorno hermético: debe fijarse ANTES de importar app.* ---
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres:devpassword@localhost:5433/forobuap_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DEV_MODE"] = "true"
os.environ["DISABLE_DEV_PIN"] = "false"
os.environ["ADMIN_PASSWORD"] = "test-admin"
os.environ["RESEND_API_KEY"] = ""      # sin correos reales: el PIN se devuelve como devPin
os.environ["emailVerifierKey"] = ""    # sin llamadas a Hunter

import asyncpg  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import db  # noqa: E402
from app.main import app  # noqa: E402

TEST_DB_NAME = urlparse(TEST_DATABASE_URL).path.lstrip("/")
assert TEST_DB_NAME.endswith("_test"), "TEST_DATABASE_URL debe apuntar a una BD cuyo nombre termine en '_test'."


async def _ensure_test_database() -> None:
    admin_url = urlparse(TEST_DATABASE_URL)._replace(path="/postgres").geturl()
    conn = await asyncpg.connect(admin_url, timeout=5)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1;", TEST_DB_NAME)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}";')
    finally:
        await conn.close()


@pytest_asyncio.fixture
async def database():
    """Conecta a la BD de pruebas, crea tablas y las deja vacías antes de cada test."""
    try:
        await _ensure_test_database()
        await db.connect()
    except Exception as exc:  # BD no disponible -> se omiten los tests de integración
        pytest.skip(f"Postgres de pruebas no disponible: {exc}")
    await db.init_tables()
    async with db.pool.acquire() as conn:
        await conn.execute(
            "TRUNCATE plan_proposal_votes, plan_proposals, forum_posts, forum_pins, "
            "forum_users, plans, faculties RESTART IDENTITY CASCADE;"
        )
    yield db
    await db.disconnect()
    db.pool = None


@pytest_asyncio.fixture
async def client(database):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def governance(monkeypatch):
    """Umbrales de votación bajos para poder probar la auto-aprobación con pocos usuarios."""
    monkeypatch.setattr(settings, "AUTO_APPROVE_MIN_VOTES", 2)
    monkeypatch.setattr(settings, "AUTO_APPROVE_RATIO", 0.51)


async def register_user(client: AsyncClient, username: str, email: str | None = None, password: str = "secret123") -> dict:
    """Flujo real: send_pin -> verify_pin -> register. Devuelve {'username', 'emailHash', 'email'}."""
    email = email or f"{username.lower()}@alumno.buap.mx"
    res = await client.post("/api/auth", json={"action": "send_pin", "email": email})
    assert res.status_code == 200, res.text
    pin = res.json()["devPin"]
    res = await client.post("/api/auth", json={"action": "verify_pin", "email": email, "pin": pin})
    assert res.status_code == 200, res.text
    res = await client.post(
        "/api/auth",
        json={"action": "register", "email": email, "pin": pin, "username": username, "password": password},
    )
    assert res.status_code == 200, res.text
    user = res.json()["user"]
    return {"username": user["username"], "emailHash": user["emailHash"], "email": email, "password": password}


SAMPLE_COURSES = [{"id": "C1", "name": "Programación", "credits": 8, "semester": 1}]
