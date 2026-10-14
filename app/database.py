import logging

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

db = Database()
