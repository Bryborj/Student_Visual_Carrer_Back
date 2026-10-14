import json
import logging
from pathlib import Path

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

class Database:
    pool: asyncpg.Pool | None = None

    async def connect(self):
        db_url = settings.get_database_url()
        logger.info("Connecting to database...")
        self.pool = await asyncpg.create_pool(
            dsn=db_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        logger.info("Database pool established.")

    async def disconnect(self):
        if self.pool:
            logger.info("Closing database pool...")
            await self.pool.close()
            logger.info("Database pool closed.")

    async def seed_initial_data(self, conn):
        """Puebla automáticamente las carreras oficiales si la tabla plans está vacía."""
        seed_path = Path(__file__).parent / "data" / "initial_seed.json"
        if not seed_path.exists():
            return

        plans_count = await conn.fetchval("SELECT count(*) FROM plans;")
        if plans_count and plans_count > 0:
            return

        logger.info(f"Poblando datos iniciales desde {seed_path.name}...")
        try:
            with open(seed_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for fac in data.get("faculties", []):
                await conn.execute("""
                    INSERT INTO faculties (id, name, logo_url)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (name) DO UPDATE SET logo_url = EXCLUDED.logo_url;
                """, fac["id"], fac["name"], fac.get("logo_url"))

            for plan in data.get("plans", []):
                courses_json = json.dumps(plan["courses"]) if not isinstance(plan["courses"], str) else plan["courses"]
                electives_json = json.dumps(plan.get("electives", [])) if not isinstance(plan.get("electives", []), str) else plan.get("electives", [])
                await conn.execute("""
                    INSERT INTO plans (id, career, modalidad, faculty_id, courses, electives, min_credits, max_credits)
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7, $8)
                    ON CONFLICT (career, modalidad) DO NOTHING;
                """, plan["id"], plan["career"], plan.get("modalidad", "Escolarizada"), plan.get("faculty_id"),
                     courses_json, electives_json, plan.get("min_credits"), plan.get("max_credits"))

            # Sincronizar secuencias serial de PostgreSQL
            await conn.execute("SELECT setval(pg_get_serial_sequence('faculties', 'id'), coalesce(max(id), 1)) FROM faculties;")
            await conn.execute("SELECT setval(pg_get_serial_sequence('plans', 'id'), coalesce(max(id), 1)) FROM plans;")
            logger.info("Datos iniciales de planes y facultades cargados exitosamente.")
        except Exception as e:
            logger.warning(f"No se pudieron cargar los datos de semilla iniciales: {e}")

    async def init_tables(self):
        if not self.pool:
            raise RuntimeError("Database pool not connected.")

        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS faculties (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    logo_url TEXT
                );

                CREATE TABLE IF NOT EXISTS plans (
                    id SERIAL PRIMARY KEY,
                    career VARCHAR(255) NOT NULL,
                    modalidad VARCHAR(100) DEFAULT 'Escolarizada',
                    faculty_id INTEGER REFERENCES faculties(id) ON DELETE SET NULL,
                    courses JSONB NOT NULL DEFAULT '[]'::jsonb,
                    electives JSONB DEFAULT '[]'::jsonb,
                    min_credits INTEGER,
                    max_credits INTEGER,
                    UNIQUE(career, modalidad)
                );

                CREATE TABLE IF NOT EXISTS forum_users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    email_hash VARCHAR(255) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS forum_pins (
                    id SERIAL PRIMARY KEY,
                    email_hash VARCHAR(255) UNIQUE NOT NULL,
                    pin VARCHAR(20) NOT NULL,
                    expires_at BIGINT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS forum_posts (
                    id VARCHAR(50) PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    career VARCHAR(255) DEFAULT 'General',
                    author VARCHAR(100) NOT NULL,
                    email_hash VARCHAR(255) NOT NULL,
                    likes INTEGER DEFAULT 0,
                    liked_by JSONB DEFAULT '[]'::jsonb,
                    comments JSONB DEFAULT '[]'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS plan_proposals (
                    id VARCHAR(50) PRIMARY KEY,
                    career VARCHAR(255) NOT NULL,
                    modalidad VARCHAR(100) DEFAULT 'Escolarizada',
                    author_username VARCHAR(100) NOT NULL,
                    author_email_hash VARCHAR(255) NOT NULL,
                    reason TEXT NOT NULL,
                    proposed_courses JSONB NOT NULL DEFAULT '[]'::jsonb,
                    proposed_electives JSONB DEFAULT '[]'::jsonb,
                    min_credits INTEGER,
                    max_credits INTEGER,
                    status VARCHAR(50) DEFAULT 'voting',
                    votes_for INTEGER DEFAULT 0,
                    votes_against INTEGER DEFAULT 0,
                    admin_feedback TEXT,
                    voting_ends_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP WITH TIME ZONE
                );

                CREATE TABLE IF NOT EXISTS plan_proposal_votes (
                    id SERIAL PRIMARY KEY,
                    proposal_id VARCHAR(50) REFERENCES plan_proposals(id) ON DELETE CASCADE,
                    voter_email_hash VARCHAR(255) NOT NULL,
                    voter_username VARCHAR(100) NOT NULL,
                    vote_type VARCHAR(10) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(proposal_id, voter_email_hash)
                );
            """)
            logger.info("Database tables verified and ready.")
            await self.seed_initial_data(conn)

db = Database()
