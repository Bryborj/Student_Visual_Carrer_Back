import json
from fastapi import APIRouter, HTTPException, Query
from app.database import db

router = APIRouter(tags=["Plans"])

@router.get("/plans-list")
async def get_plans_list():
    """Retorna el listado de planes de estudio disponibles."""
    if not db.pool:
        raise HTTPException(status_code=500, detail="Database not connected.")

    async with db.pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                p.id AS "_id",
                p.career,
                p.modalidad,
                f.name AS faculty,
                f.logo_url
            FROM plans p
            LEFT JOIN faculties f ON p.faculty_id = f.id;
        """)

        return [
            {
                "_id": str(r["_id"]) if r["_id"] else None,
                "career": r["career"],
                "modalidad": r["modalidad"],
                "faculty": r["faculty"],
                "logo_url": r["logo_url"]
            }
            for r in rows
        ]

@router.get("/plan")
async def get_plan(
    career: str = Query("Ingeniería en Ciencias de la Computación"),
    modalidad: str | None = Query(None)
):
    """Retorna la información y cursos detallados de un plan de estudios específico."""
    if not db.pool:
        raise HTTPException(status_code=500, detail="Database not connected.")

    async with db.pool.acquire() as conn:
        query = """
            SELECT 
                p.id AS "_id",
                p.career,
                p.modalidad,
                p.courses,
                p.electives,
                p.min_credits,
                p.max_credits,
                f.name AS faculty,
                f.logo_url
            FROM plans p
            LEFT JOIN faculties f ON p.faculty_id = f.id
            WHERE p.career = $1
        """
        params = [career]

        if modalidad:
            query += " AND p.modalidad = $2"
            params.append(modalidad)

        query += " LIMIT 1;"

        row = await conn.fetchrow(query, *params)
        if not row:
            raise HTTPException(status_code=404, detail="Plan not found")

        plan = dict(row)
        plan["_id"] = str(plan["_id"]) if plan.get("_id") else None

        # Deserializar JSONB si viene como string
        if isinstance(plan.get("courses"), str):
            plan["courses"] = json.loads(plan["courses"])
        if isinstance(plan.get("electives"), str):
            plan["electives"] = json.loads(plan["electives"])

        return plan
