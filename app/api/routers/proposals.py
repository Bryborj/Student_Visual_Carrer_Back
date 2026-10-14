import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import resolve_authenticated_user
from app.config import settings
from app.database import db
from app.services.voting_service import VotingService

router = APIRouter(prefix="/proposals", tags=["Proposals"])

class CreateProposalRequest(BaseModel):
    career: str
    username: str | None = None
    emailHash: str | None = None
    reason: str
    courses: list
    electives: list = []
    min_credits: int | None = None
    max_credits: int | None = None

class VoteRequest(BaseModel):
    username: str | None = None
    emailHash: str | None = None
    voteType: str = "for"  # 'for' o 'against'

def format_proposal(row: dict, user_vote: str | None = None) -> dict:
    courses = row.get("proposed_courses", [])
    electives = row.get("proposed_electives", [])
    if isinstance(courses, str):
        courses = json.loads(courses)
    if isinstance(electives, str):
        electives = json.loads(electives)

    return {
        "id": row["id"],
        "career": row["career"],
        "author": row["author_username"],
        "emailHash": row["author_email_hash"],
        "reason": row["reason"],
        "courses": courses,
        "electives": electives,
        "minCredits": row.get("min_credits"),
        "maxCredits": row.get("max_credits"),
        "status": row["status"],
        "votesFor": row.get("votes_for", 0),
        "votesAgainst": row.get("votes_against", 0),
        "userVote": user_vote,
        "adminFeedback": row.get("admin_feedback"),
        "votingEndsAt": row["voting_ends_at"].isoformat() if row.get("voting_ends_at") else None,
        "createdAt": row["created_at"].isoformat() if row.get("created_at") else None,
        "resolvedAt": row["resolved_at"].isoformat() if row.get("resolved_at") else None
    }

@router.post("")
async def create_proposal(
    req: CreateProposalRequest,
    authorization: str | None = Header(None)
):
    """Permite a un alumno registrado proponer una actualización a un plan de estudios."""
    if not db.pool:
        raise HTTPException(status_code=500, detail="Database not connected.")

    user = await resolve_authenticated_user(authorization, req.username, req.emailHash)
    author_username = user["username"]
    author_email_hash = user["emailHash"]

    if not req.reason.strip():
        raise HTTPException(status_code=400, detail="La justificación o motivo del cambio es obligatoria.")

    if not req.courses:
        raise HTTPException(status_code=400, detail="El plan propuesto debe incluir las materias.")

    async with db.pool.acquire() as conn:
        proposal_id = str(uuid.uuid4())[:8]
        voting_ends_at = datetime.now(timezone.utc) + timedelta(days=settings.VOTE_WINDOW_DAYS)

        courses_json = json.dumps(req.courses)
        electives_json = json.dumps(req.electives)

        await conn.execute("""
            INSERT INTO plan_proposals (
                id, career, author_username, author_email_hash, reason,
                proposed_courses, proposed_electives, min_credits, max_credits,
                status, votes_for, votes_against, voting_ends_at, created_at
            ) VALUES (
                $1, $2, $3, $4, $5,
                $6::jsonb, $7::jsonb, $8, $9,
                'voting', 1, 0, $10, NOW()
            );
        """, proposal_id, req.career, author_username, author_email_hash, req.reason,
             courses_json, electives_json, req.min_credits, req.max_credits, voting_ends_at)

        # Registrar el voto inicial a favor del autor
        await conn.execute("""
            INSERT INTO plan_proposal_votes (proposal_id, voter_email_hash, voter_username, vote_type, created_at)
            VALUES ($1, $2, $3, 'for', NOW());
        """, proposal_id, author_email_hash, author_username)

        row = await conn.fetchrow("SELECT * FROM plan_proposals WHERE id = $1;", proposal_id)
        return {"success": True, "proposal": format_proposal(dict(row), user_vote="for")}

@router.get("")
async def list_proposals(
    career: str | None = Query(None),
    status: str | None = Query(None),
    user_email_hash: str | None = Query(None)
):
    """Lista las propuestas de actualización de planes con sus votos y estado."""
    if not db.pool:
        raise HTTPException(status_code=500, detail="Database not connected.")

    async with db.pool.acquire() as conn:
        query = "SELECT * FROM plan_proposals WHERE 1=1"
        params = []

        if career and career != "Todas":
            params.append(career)
            query += f" AND career = ${len(params)}"

        if status and status != "all":
            params.append(status)
            query += f" AND status = ${len(params)}"

        query += " ORDER BY created_at DESC LIMIT 50;"
        rows = await conn.fetch(query, *params)

        user_votes_map = {}
        if user_email_hash:
            votes = await conn.fetch(
                "SELECT proposal_id, vote_type FROM plan_proposal_votes WHERE voter_email_hash = $1;",
                user_email_hash
            )
            user_votes_map = {v["proposal_id"]: v["vote_type"] for v in votes}

        return [
            format_proposal(dict(r), user_vote=user_votes_map.get(r["id"]))
            for r in rows
        ]

@router.get("/{proposal_id}")
async def get_proposal(proposal_id: str, user_email_hash: str | None = Query(None)):
    """Obtiene el detalle de una propuesta específica."""
    if not db.pool:
        raise HTTPException(status_code=500, detail="Database not connected.")

    async with db.pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM plan_proposals WHERE id = $1;", proposal_id)
        if not row:
            raise HTTPException(status_code=404, detail="Propuesta no encontrada.")

        user_vote = None
        if user_email_hash:
            v_row = await conn.fetchrow(
                "SELECT vote_type FROM plan_proposal_votes WHERE proposal_id = $1 AND voter_email_hash = $2;",
                proposal_id, user_email_hash
            )
            if v_row:
                user_vote = v_row["vote_type"]

        return format_proposal(dict(row), user_vote=user_vote)

@router.post("/{proposal_id}/vote")
async def vote_proposal(
    proposal_id: str,
    req: VoteRequest,
    authorization: str | None = Header(None)
):
    """Permite a un alumno registrado emitir su voto a favor o en contra de una propuesta."""
    if not db.pool:
        raise HTTPException(status_code=500, detail="Database not connected.")

    user = await resolve_authenticated_user(authorization, req.username, req.emailHash)
    voter_username = user["username"]
    voter_email_hash = user["emailHash"]

    result = await VotingService.cast_vote(
        proposal_id=proposal_id,
        voter_username=voter_username,
        voter_email_hash=voter_email_hash,
        vote_type=req.voteType
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Error al registrar el voto."))

    return result
