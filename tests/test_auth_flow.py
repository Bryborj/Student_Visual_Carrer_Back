from tests.conftest import register_user


async def test_full_registration_and_login_flow(client):
    user = await register_user(client, "LoboDev", "lobo@alumno.buap.mx")

    # Login por nombre de usuario (case-insensitive)
    res = await client.post("/api/auth", json={"action": "login", "identifier": "lobodev", "password": "secret123"})
    assert res.status_code == 200
    assert res.json()["user"]["emailHash"] == user["emailHash"]

    # Login por correo
    res = await client.post(
        "/api/auth", json={"action": "login", "identifier": "lobo@alumno.buap.mx", "password": "secret123"}
    )
    assert res.status_code == 200
    assert res.json()["user"]["username"] == "LoboDev"


async def test_login_wrong_password(client):
    await register_user(client, "Loba")
    res = await client.post("/api/auth", json={"action": "login", "identifier": "Loba", "password": "mal-password"})
    assert res.status_code == 401


async def test_cannot_send_pin_to_registered_email(client):
    user = await register_user(client, "Repetido")
    res = await client.post("/api/auth", json={"action": "send_pin", "email": user["email"]})
    assert res.status_code == 400
    assert "ya está registrado" in res.json()["detail"]


async def test_verify_pin_rejects_wrong_pin(client):
    email = "pin@alumno.buap.mx"
    await client.post("/api/auth", json={"action": "send_pin", "email": email})
    res = await client.post("/api/auth", json={"action": "verify_pin", "email": email, "pin": "000000"})
    assert res.status_code == 400


async def test_register_rejects_duplicate_username_and_short_password(client):
    await register_user(client, "Unico")

    email = "otro@alumno.buap.mx"
    pin = (await client.post("/api/auth", json={"action": "send_pin", "email": email})).json()["devPin"]

    res = await client.post(
        "/api/auth",
        json={"action": "register", "email": email, "pin": pin, "username": "unico", "password": "secret123"},
    )
    assert res.status_code == 400 and "ocupado" in res.json()["detail"]

    res = await client.post(
        "/api/auth",
        json={"action": "register", "email": email, "pin": pin, "username": "Nuevo", "password": "123"},
    )
    assert res.status_code == 400
