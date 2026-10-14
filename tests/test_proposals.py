from tests.conftest import SAMPLE_COURSES, register_user

CAREER = "Ingeniería en Ciencias de la Computación"


async def _propose(client, user, **overrides):
    payload = {
        "career": CAREER,
        "username": user["username"],
        "emailHash": user["emailHash"],
        "reason": "Actualizar créditos",
        "courses": SAMPLE_COURSES,
        "min_credits": 250,
        "max_credits": 300,
        **overrides,
    }
    return await client.post("/api/proposals", json=payload)


async def _vote(client, proposal_id, user, vote_type="for"):
    return await client.post(
        f"/api/proposals/{proposal_id}/vote",
        json={"username": user["username"], "emailHash": user["emailHash"], "voteType": vote_type},
    )


async def test_create_requires_registered_user_and_reason(client):
    res = await client.post(
        "/api/proposals",
        json={
            "career": CAREER, "username": "fantasma", "emailHash": "x", "reason": "r", "courses": SAMPLE_COURSES,
        },
    )
    assert res.status_code == 401

    user = await register_user(client, "Autor0")
    assert (await _propose(client, user, reason="  ")).status_code == 400
    assert (await _propose(client, user, courses=[])).status_code == 400


async def test_create_adds_author_vote_and_lists(client):
    user = await register_user(client, "Autor1")
    res = await _propose(client, user)
    assert res.status_code == 200
    proposal = res.json()["proposal"]
    assert proposal["status"] == "voting" and proposal["votesFor"] == 1 and proposal["userVote"] == "for"

    listed = (await client.get("/api/proposals", params={"user_email_hash": user["emailHash"]})).json()
    assert [p["id"] for p in listed] == [proposal["id"]]
    assert listed[0]["userVote"] == "for"

    assert (await client.get(f"/api/proposals/{proposal['id']}")).status_code == 200
    assert (await client.get("/api/proposals/no-existe")).status_code == 404


async def test_vote_below_threshold_keeps_voting(client, governance):
    author = await register_user(client, "Autor2")
    await register_user(client, "Votante2")
    third = await register_user(client, "Votante3")
    proposal_id = (await _propose(client, author)).json()["proposal"]["id"]

    # Voto en contra del tercero: 1 a favor / 1 en contra -> sigue en votación
    res = await _vote(client, proposal_id, third, "against")
    assert res.status_code == 200
    body = res.json()
    assert body["auto_approved"] is False and body["votes_for"] == 1 and body["votes_against"] == 1


async def test_vote_reaches_threshold_auto_approves_and_updates_plan(client, governance):
    author = await register_user(client, "Autor3")
    voter = await register_user(client, "Votante4")
    await register_user(client, "Votante5")
    proposal_id = (await _propose(client, author)).json()["proposal"]["id"]

    res = await _vote(client, proposal_id, voter, "for")  # 2 de 3 usuarios >= 51 %, y >= 2 votos
    assert res.status_code == 200 and res.json()["auto_approved"] is True

    assert (await client.get(f"/api/proposals/{proposal_id}")).json()["status"] == "auto_approved"
    plan = (await client.get("/api/plan", params={"career": CAREER})).json()
    assert plan["courses"][0]["name"] == "Programación"
    assert plan["min_credits"] == 250

    # Ya no admite más votos
    other = await register_user(client, "Tardio")
    assert (await _vote(client, proposal_id, other)).status_code == 400


async def test_vote_requires_registered_user_and_existing_proposal(client):
    user = await register_user(client, "Autor4")
    proposal_id = (await _propose(client, user)).json()["proposal"]["id"]

    ghost = {"username": "fantasma", "emailHash": "nada"}
    assert (await _vote(client, proposal_id, ghost)).status_code == 401
    assert (await _vote(client, "no-existe", user)).status_code == 400
