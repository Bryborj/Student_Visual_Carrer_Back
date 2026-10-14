from app.api.routers.proposals import format_proposal


def test_format_proposal():
    mock_row = {
        "id": "prop123",
        "career": "Ingeniería en Ciencias de la Computación",
        "modalidad": "Escolarizada",
        "author_username": "LoboDev",
        "author_email_hash": "hash123456",
        "reason": "Actualización de optativas y créditos",
        "proposed_courses": [{"name": "IA Avanzada", "credits": 6}],
        "proposed_electives": [],
        "min_credits": 250,
        "max_credits": 300,
        "status": "voting",
        "votes_for": 12,
        "votes_against": 1,
        "admin_feedback": None,
        "voting_ends_at": None,
        "created_at": None,
        "resolved_at": None
    }

    formatted = format_proposal(mock_row, user_vote="for")
    assert formatted["id"] == "prop123"
    assert formatted["author"] == "LoboDev"
    assert formatted["votesFor"] == 12
    assert formatted["userVote"] == "for"
    assert len(formatted["courses"]) == 1
    assert formatted["courses"][0]["name"] == "IA Avanzada"
