import json
import logging
from datetime import datetime, timezone

from app.config import settings
from app.database import db
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

class VotingService:
    @staticmethod
    async def apply_proposal_to_plan(conn, proposal: dict):
        """Aplica los cambios de una propuesta directamente sobre la tabla oficial 'plans'."""
        career = proposal["career"]
        modalidad = proposal.get("modalidad") or "Escolarizada"
        courses = proposal["proposed_courses"]
        electives = proposal.get("proposed_electives") or []
        min_credits = proposal.get("min_credits")
        max_credits = proposal.get("max_credits")

        courses_json = json.dumps(courses) if not isinstance(courses, str) else courses
        electives_json = json.dumps(electives) if not isinstance(electives, str) else electives

        await conn.execute("""
            INSERT INTO plans (career, modalidad, courses, electives, min_credits, max_credits)
            VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $6)
            ON CONFLICT (career, modalidad) DO UPDATE SET
                courses = EXCLUDED.courses,
                electives = EXCLUDED.electives,
                min_credits = EXCLUDED.min_credits,
                max_credits = EXCLUDED.max_credits;
        """, career, modalidad, courses_json, electives_json, min_credits, max_credits)

        logger.info(f"✅ Plan '{career} ({modalidad})' actualizado exitosamente en base de datos.")

    @classmethod
    async def cast_vote(cls, proposal_id: str, voter_username: str, voter_email_hash: str, vote_type: str = "for") -> dict:
        """
        Registra el voto de un alumno y evalúa si se cumple la condición de auto-aprobación comunitaria.
        """
        if not db.pool:
            raise RuntimeError("Database pool not available.")

        async with db.pool.acquire() as conn:
            # 1. Obtener la propuesta
            row = await conn.fetchrow("SELECT * FROM plan_proposals WHERE id = $1;", proposal_id)
            if not row:
                return {"success": False, "error": "Propuesta no encontrada."}

            proposal = dict(row)
            if proposal["status"] != "voting":
                return {
                    "success": False,
                    "error": f"La propuesta ya no está en votación (Estado: {proposal['status']})."
                }

            # Verificar si expiró la ventana de tiempo
            now = datetime.now(timezone.utc)
            if proposal.get("voting_ends_at") and proposal["voting_ends_at"] < now:
                await conn.execute("UPDATE plan_proposals SET status = 'expired' WHERE id = $1;", proposal_id)
                return {
                    "success": False,
                    "error": "El periodo de votación ha concluido. La propuesta ha pasado a revisión del staff."
                }

            # 2. Registrar o actualizar voto (1 voto por alumno)
            await conn.execute("""
                INSERT INTO plan_proposal_votes (proposal_id, voter_email_hash, voter_username, vote_type, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (proposal_id, voter_email_hash) DO UPDATE SET
                    vote_type = EXCLUDED.vote_type,
                    created_at = NOW();
            """, proposal_id, voter_email_hash, voter_username, vote_type)

            # 3. Recalcular votos
            votes_for = await conn.fetchval(
                "SELECT COUNT(*) FROM plan_proposal_votes WHERE proposal_id = $1 AND vote_type = 'for';",
                proposal_id
            ) or 0

            votes_against = await conn.fetchval(
                "SELECT COUNT(*) FROM plan_proposal_votes WHERE proposal_id = $1 AND vote_type = 'against';",
                proposal_id
            ) or 0

            # 4. Obtener cantidad total de usuarios registrados en el sistema
            total_users = await conn.fetchval("SELECT COUNT(*) FROM forum_users;") or 1

            # 5. Evaluar umbral de auto-aprobación comunitaria
            # Cumplimiento: votos a favor alcanzan el mínimo configurado Y el ratio de quórum respecto a los usuarios registrados
            current_ratio = votes_for / max(total_users, 1)
            auto_approved = (
                votes_for >= settings.AUTO_APPROVE_MIN_VOTES and
                current_ratio >= settings.AUTO_APPROVE_RATIO
            )

            logger.info(
                f"Voto en propuesta {proposal_id}: a favor={votes_for}, en contra={votes_against}, "
                f"total_usuarios={total_users}, ratio={current_ratio:.2f} (meta: >= {settings.AUTO_APPROVE_RATIO}, "
                f"min_votos: {settings.AUTO_APPROVE_MIN_VOTES}) -> auto_aprobado={auto_approved}"
            )

            if auto_approved:
                # Transacción atómica: aplicar cambios al plan oficial y marcar auto_approved
                async with conn.transaction():
                    await cls.apply_proposal_to_plan(conn, proposal)
                    await conn.execute("""
                        UPDATE plan_proposals
                        SET status = 'auto_approved',
                            votes_for = $1,
                            votes_against = $2,
                            resolved_at = NOW()
                        WHERE id = $3;
                    """, votes_for, votes_against, proposal_id)

                # Notificar a staff/admin vía Resend
                await EmailService.send_auto_approval_notification(
                    career=proposal["career"],
                    proposal_id=proposal_id,
                    votes=votes_for,
                    author=proposal["author_username"]
                )

                return {
                    "success": True,
                    "auto_approved": True,
                    "votes_for": votes_for,
                    "votes_against": votes_against,
                    "total_users": total_users,
                    "message": "¡Meta de votos alcanzada! El plan ha sido actualizado automáticamente en vivo."
                }

            # Si aún no alcanza el umbral, solo actualizamos contadores
            await conn.execute("""
                UPDATE plan_proposals
                SET votes_for = $1,
                    votes_against = $2
                WHERE id = $3;
            """, votes_for, votes_against, proposal_id)

            return {
                "success": True,
                "auto_approved": False,
                "votes_for": votes_for,
                "votes_against": votes_against,
                "total_users": total_users,
                "message": "Voto registrado exitosamente."
            }
