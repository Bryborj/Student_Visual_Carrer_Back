import pytest

from app.database import db


@pytest.mark.asyncio
async def test_auto_seed_populates_official_plans(database):
    async with db.pool.acquire() as conn:
        # Aseguramos que esté vacío
        await conn.execute("TRUNCATE plans, faculties RESTART IDENTITY CASCADE;")
        count_before = await conn.fetchval("SELECT count(*) FROM plans;")
        assert count_before == 0

        # Ejecutamos el seed
        await db.seed_initial_data(conn)

        count_after = await conn.fetchval("SELECT count(*) FROM plans;")
        fac_count = await conn.fetchval("SELECT count(*) FROM faculties;")
        assert count_after == 3
        assert fac_count == 2

        # Verificar que contiene la carrera principal y sus cursos
        icc = await conn.fetchrow(
            "SELECT career, courses FROM plans WHERE career = $1;",
            "Ingeniería en Ciencias de la Computación"
        )
        assert icc is not None
        courses = icc["courses"]
        if isinstance(courses, str):
            import json
            courses = json.loads(courses)
        assert len(courses) > 0
        assert "cluster" in courses[0]

        # Segunda ejecución no duplica registros
        await db.seed_initial_data(conn)
        assert await conn.fetchval("SELECT count(*) FROM plans;") == 3
