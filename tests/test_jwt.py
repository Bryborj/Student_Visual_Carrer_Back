from datetime import timedelta

import pytest

from app.security import create_access_token, decode_access_token
from tests.conftest import register_user


def test_token_creation_and_decoding():
    payload = {"sub": "LoboDev", "username": "LoboDev", "emailHash": "hash123"}
    token = create_access_token(payload, expires_delta=timedelta(minutes=15))
    decoded = decode_access_token(token)

    assert decoded is not None
    assert decoded["sub"] == "LoboDev"
    assert decoded["username"] == "LoboDev"
    assert decoded["emailHash"] == "hash123"
    assert "exp" in decoded


def test_token_decoding_invalid_or_expired():
    assert decode_access_token("token.invalido.falso") is None

    # Token expirado (-5 minutos)
    payload = {"sub": "Expirado"}
    expired_token = create_access_token(payload, expires_delta=timedelta(minutes=-5))
    assert decode_access_token(expired_token) is None


@pytest.mark.asyncio
async def test_auth_login_and_register_returns_valid_jwt(client):
    user = await register_user(client, "LoboToken", "lobotoken@alumno.buap.mx")
    assert "token" in user and user["token"]

    decoded = decode_access_token(user["token"])
    assert decoded["sub"] == "LoboToken"
    assert decoded["emailHash"] == user["emailHash"]

    # Login también devuelve token válido
    res = await client.post(
        "/api/auth",
        json={"action": "login", "identifier": "LoboToken", "password": "secret123"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "token" in data and data["token"]
    login_decoded = decode_access_token(data["token"])
    assert login_decoded["sub"] == "LoboToken"


@pytest.mark.asyncio
async def test_forum_uses_jwt_identity_preventing_spoofing(client):
    legit_user = await register_user(client, "Legitimo")
    attacker = await register_user(client, "Atacante")

    headers = {"Authorization": f"Bearer {legit_user['token']}"}

    # Atacante intenta mandar el username de la víctima en el cuerpo con su propio token
    spoofed_body = {
        "action": "create_post",
        "title": "Post Seguro",
        "content": "Verificando identidad criptográfica",
        "category": "Dudas",
        "username": "Atacante",  # en el cuerpo dice Atacante, pero el token es de Legitimo
        "emailHash": attacker["emailHash"]
    }

    res = await client.post("/api/forum", json=spoofed_body, headers=headers)
    assert res.status_code == 200
    post = res.json()
    # El autor debe ser Legitimo (el dueño del token), ignorando el cuerpo engañoso
    assert post["author"] == "Legitimo"
    assert post["emailHash"] == legit_user["emailHash"]


@pytest.mark.asyncio
async def test_proposals_uses_jwt_identity(client):
    user = await register_user(client, "ProponenteJWT")
    headers = {"Authorization": f"Bearer {user['token']}"}

    res = await client.post(
        "/api/proposals",
        json={
            "career": "Ingeniería en Ciencias de la Computación",
            "reason": "Propuesta firmada con token",
            "courses": [{"id": "C1", "name": "Materia", "credits": 5}]
        },
        headers=headers
    )
    assert res.status_code == 200
    proposal = res.json()["proposal"]
    assert proposal["author"] == "ProponenteJWT"
    assert proposal["emailHash"] == user["emailHash"]
