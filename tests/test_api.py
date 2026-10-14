import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Student_Visual_Carrer_Back"
        assert data["email_sender"] == "community@forobuap.zrootsh.com"

@pytest.mark.asyncio
async def test_auth_domain_validation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Intento de PIN con correo que no es BUAP
        response = await ac.post("/api/auth", json={
            "action": "send_pin",
            "email": "usuario@gmail.com"
        })
        assert response.status_code == 400
        assert "buap.mx" in response.json()["detail"]

@pytest.mark.asyncio
async def test_admin_wrong_password():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/admin", json={
            "password": "incorrect_password",
            "action": "verify"
        })
        assert response.status_code == 401
