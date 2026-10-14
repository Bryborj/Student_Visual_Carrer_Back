import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.routers.proposals import format_proposal
from app.config import settings
from app.database import db
from app.services.voting_service import VotingService

router = APIRouter(tags=["Admin"])

class AdminActionRequest(BaseModel):
    password: str
    action: str
    payload: dict | None = None
    proposalId: str | None = None
    feedback: str | None = None

@router.post("/admin")
async def handle_admin(req: AdminActionRequest):
    """
    Endpoint de administración.
    Permite verificar contraseña, agregar planes y aprobar/rechazar propuestas de alumnos.
    """
    if not settings.ADMIN_PASSWORD or req.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="No autorizado. Contraseña incorrecta.")

    if not db.pool:
        raise HTTPException(status_code=500, detail="Database not connected.")

    action = req.action

    if action == "verify":
        return {"success": True, "message": "Autenticado"}

    if action == "addPlan":
        payload = req.payload
        if not payload or not payload.get("career") or not payload.get("courses"):
            raise HTTPException(status_code=400, detail="El plan debe contener career y courses.")

        career = payload["career"]
        modalidad = payload.get("modalidad") or payload.get("mode") or "Escolarizada"
        faculty_name = payload.get("faculty")
        logo_url = payload.get("logo_url", "")
        courses = payload.get("courses", [])
        electives = payload.get("electives", [])
        min_credits = payload.get("min_credits")
        max_credits = payload.get("max_credits")

        async with db.pool.acquire() as conn:
            faculty_id = None
            if faculty_name:
                fac_row = await conn.fetchrow("""
                    INSERT INTO faculties (name, logo_url)
                    VALUES ($1, $2)
                    ON CONFLICT (name) DO UPDATE SET
                        logo_url = COALESCE(NULLIF(EXCLUDED.logo_url, ''), faculties.logo_url)
                    RETURNING id;
                """, faculty_name, logo_url)
                faculty_id = fac_row["id"]

            await conn.execute("""
                INSERT INTO plans (career, modalidad, faculty_id, courses, electives, min_credits, max_credits)
                VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6, $7)
                ON CONFLICT (career, modalidad) DO UPDATE SET
                    faculty_id = EXCLUDED.faculty_id,
                    courses = EXCLUDED.courses,
                    electives = EXCLUDED.electives,
                    min_credits = EXCLUDED.min_credits,
                    max_credits = EXCLUDED.max_credits;
            """, career, modalidad, faculty_id, json.dumps(courses), json.dumps(electives), min_credits, max_credits)

        return {"success": True, "message": "Plan agregado/actualizado correctamente."}

    if action == "get_proposals":
        async with db.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM plan_proposals ORDER BY created_at DESC LIMIT 100;")
            return {"success": True, "proposals": [format_proposal(dict(r)) for r in rows]}

    if action == "approve_proposal":
        proposal_id = req.proposalId
        if not proposal_id:
            raise HTTPException(status_code=400, detail="proposalId requerido.")

        async with db.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM plan_proposals WHERE id = $1;", proposal_id)
            if not row:
                raise HTTPException(status_code=404, detail="Propuesta no encontrada.")

            proposal = dict(row)
            async with conn.transaction():
                await VotingService.apply_proposal_to_plan(conn, proposal)
                await conn.execute("""
                    UPDATE plan_proposals
                    SET status = 'admin_approved',
                        admin_feedback = $1,
                        resolved_at = NOW()
                    WHERE id = $2;
                """, req.feedback or "Aprobado manualmente por la administración.", proposal_id)

        return {"success": True, "message": "Propuesta aprobada y aplicada al plan oficial exitosamente."}

    if action == "reject_proposal":
        proposal_id = req.proposalId
        if not proposal_id:
            raise HTTPException(status_code=400, detail="proposalId requerido.")

        async with db.pool.acquire() as conn:
            await conn.execute("""
                UPDATE plan_proposals
                SET status = 'rejected',
                    admin_feedback = $1,
                    resolved_at = NOW()
                WHERE id = $2;
            """, req.feedback or "Rechazada por el administrador.", proposal_id)

        return {"success": True, "message": "Propuesta rechazada."}

    raise HTTPException(status_code=400, detail="Acción desconocida.")
