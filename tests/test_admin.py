from tests.conftest import SAMPLE_COURSES, register_user

ADMIN = "test-admin"
CAREER = "Licenciatura en Física"


async def _admin(client, action, **extra):
    return await client.post("/api/admin", json={"password": ADMIN, "action": action, **extra})


async def test_admin_verify_and_wrong_password(client):
    assert (await _admin(client, "verify")).json()["success"] is True
    res = await client.post("/api/admin", json={"password": "mal", "action": "verify"})
    assert res.status_code == 401


async def test_add_plan_then_visible_in_plans_list_and_plan(client):
    res = await _admin(
        client,
        "addPlan",
        payload={
            "career": CAREER,
            "modalidad": "Escolarizada",
            "faculty": "Facultad de Ciencias Físico Matemáticas",
            "courses": SAMPLE_COURSES,
            "min_credits": 200,
            "max_credits": 320,
        },
    )
    assert res.status_code == 200

    plans = (await client.get("/api/plans-list")).json()
    assert plans[0]["career"] == CAREER and plans[0]["faculty"].startswith("Facultad")

    plan = (await client.get("/api/plan", params={"career": CAREER})).json()
    assert plan["courses"] == SAMPLE_COURSES
    assert (await client.get("/api/plan", params={"career": "No existe"})).status_code == 404


async def test_add_plan_validation(client):
    assert (await _admin(client, "addPlan", payload={"career": CAREER})).status_code == 400


async def test_approve_and_reject_proposals(client):
    author = await register_user(client, "AutorAdm")
    base = {"career": CAREER, "username": author["username"], "emailHash": author["emailHash"], "courses": SAMPLE_COURSES}
    p1 = (await client.post("/api/proposals", json={**base, "reason": "uno"})).json()["proposal"]["id"]
    p2 = (await client.post("/api/proposals", json={**base, "reason": "dos", "modalidad": "Mixta"})).json()["proposal"]["id"]

    assert (await _admin(client, "approve_proposal", proposalId=p1, feedback="ok")).status_code == 200
    assert (await _admin(client, "reject_proposal", proposalId=p2, feedback="no")).status_code == 200

    proposals = {p["id"]: p for p in (await _admin(client, "get_proposals")).json()["proposals"]}
    assert proposals[p1]["status"] == "admin_approved" and proposals[p1]["adminFeedback"] == "ok"
    assert proposals[p2]["status"] == "rejected"

    # La aprobada quedó aplicada al plan oficial
    assert (await client.get("/api/plan", params={"career": CAREER, "modalidad": "Escolarizada"})).status_code == 200


async def test_admin_unknown_action_and_missing_proposal(client):
    assert (await _admin(client, "bogus")).status_code == 400
    assert (await _admin(client, "approve_proposal", proposalId="no-existe")).status_code == 404
    assert (await _admin(client, "approve_proposal")).status_code == 400
