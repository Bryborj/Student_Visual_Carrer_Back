from tests.conftest import register_user


async def _create_post(client, user, **overrides):
    payload = {
        "action": "create_post",
        "title": "Hola manada",
        "content": "¿Alguien tiene apuntes de Cálculo?",
        "category": "Dudas",
        "username": user["username"],
        "emailHash": user["emailHash"],
        **overrides,
    }
    return await client.post("/api/forum", json=payload)


async def test_create_list_like_and_comment(client):
    user = await register_user(client, "Foro1")

    res = await _create_post(client, user, career="Ingeniería en Ciencias de la Computación")
    assert res.status_code == 200
    post = res.json()
    assert post["author"] == "Foro1" and post["likes"] == 0

    # Listado + filtros
    assert len((await client.get("/api/forum")).json()) == 1
    assert len((await client.get("/api/forum", params={"category": "Dudas"})).json()) == 1
    assert (await client.get("/api/forum", params={"category": "Eventos"})).json() == []

    # Like y quitar like (toggle)
    like = {"action": "like_post", "postId": post["_id"], "username": user["username"], "emailHash": user["emailHash"]}
    assert (await client.post("/api/forum", json=like)).json()["likes"] == 1
    assert (await client.post("/api/forum", json=like)).json()["likes"] == 0

    # Comentario
    res = await client.post(
        "/api/forum",
        json={**like, "action": "add_comment", "commentContent": "Yo tengo, te los paso"},
    )
    assert res.status_code == 200
    assert res.json()["comments"][0]["content"] == "Yo tengo, te los paso"


async def test_forum_requires_login_fields(client):
    res = await client.post("/api/forum", json={"action": "create_post", "title": "x", "content": "y", "category": "z"})
    assert res.status_code == 401


async def test_create_post_validation_and_missing_post(client):
    user = await register_user(client, "Foro2")
    res = await _create_post(client, user, title=None)
    assert res.status_code == 400

    res = await client.post(
        "/api/forum",
        json={"action": "like_post", "postId": "no-existe", "username": user["username"], "emailHash": user["emailHash"]},
    )
    assert res.status_code == 404
