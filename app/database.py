import json
import logging
import re
from pathlib import Path

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

class Database:
    pool: asyncpg.Pool | None = None

    async def connect(self):
        db_url = settings.get_database_url()
        masked_url = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", db_url)
        logger.info(f"Connecting to database at {masked_url}...")
        self.pool = await asyncpg.create_pool(
            dsn=db_url,
            min_size=1,
            max_size=10,
            max_inactive_connection_lifetime=60.0,
            timeout=15.0,
            command_timeout=30.0,
            server_settings={
                "tcp_keepalives_idle": "30",
                "tcp_keepalives_interval": "10",
                "tcp_keepalives_count": "3",
            },
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
                    INSERT INTO plans (id, career, faculty_id, courses, electives, min_credits, max_credits)
                    VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6, $7)
                    ON CONFLICT (career) DO NOTHING;
                """, plan["id"], plan["career"], plan.get("faculty_id"),
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
                    career VARCHAR(255) UNIQUE NOT NULL,
                    faculty_id INTEGER REFERENCES faculties(id) ON DELETE SET NULL,
                    courses JSONB NOT NULL DEFAULT '[]'::jsonb,
                    electives JSONB DEFAULT '[]'::jsonb,
                    min_credits INTEGER,
                    max_credits INTEGER
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

                -- Migración segura e idempotente para eliminar columna 'modalidad' si la BD ya existía
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'plans' AND column_name = 'modalidad'
                    ) THEN
                        ALTER TABLE plans DROP CONSTRAINT IF EXISTS plans_career_modalidad_key;
                        ALTER TABLE plans DROP COLUMN IF EXISTS modalidad;
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint WHERE conname = 'plans_career_key'
                        ) THEN
                            ALTER TABLE plans ADD CONSTRAINT plans_career_key UNIQUE (career);
                        END IF;
                    END IF;

                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'plan_proposals' AND column_name = 'modalidad'
                    ) THEN
                        ALTER TABLE plan_proposals DROP COLUMN IF EXISTS modalidad;
                    END IF;
                END $$;

                -- Créditos al alumno que integró el plan y marca de propuesta de plan nuevo
                ALTER TABLE plans ADD COLUMN IF NOT EXISTS contributor_username VARCHAR(100);
                ALTER TABLE plan_proposals ADD COLUMN IF NOT EXISTS is_new_plan BOOLEAN DEFAULT FALSE;
            """)
            logger.info("Database tables verified and ready.")
            await self.seed_initial_data(conn)

db = Database()
