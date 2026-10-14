import random
import re
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.database import db
from app.security import hash_email, hash_password, verify_password
from app.services.email_service import EmailService
from app.services.hunter_service import HunterService

router = APIRouter(tags=["Auth"])

class AuthRequest(BaseModel):
    action: str
    email: str | None = None
    pin: str | None = None
    username: str | None = None
    password: str | None = None
    identifier: str | None = None

@router.post("/auth")
async def handle_auth(req: AuthRequest):
    """
    Endpoint de autenticación compatible con el frontend existente.
    Soporta: send_pin, verify_pin, register, login.
    """
    action = req.action

    # 1. ENVIAR PIN DE VERIFICACIÓN
    if action == "send_pin":
        email = req.email
        if not email or not re.match(r"^\S+@\S+\.\S+$", email):
            raise HTTPException(status_code=400, detail="Correo electrónico inválido.")

        domain = email.split("@")[1].lower()
        if "buap.mx" not in domain:
            raise HTTPException(status_code=400, detail="El correo debe ser institucional (contener buap.mx).")

        if not db.pool:
            raise HTTPException(status_code=500, detail="Database not connected.")

        email_hash = hash_email(email)

        async with db.pool.acquire() as conn:
            # Verificar si ya está registrado
            existing = await conn.fetchrow("SELECT id FROM forum_users WHERE email_hash = $1;", email_hash)
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail="Este correo institucional ya está registrado en el foro. Por favor inicia sesión."
                )

            # Verificación con Hunter API
            hunter_res = await HunterService.verify_email(email)
            if not hunter_res.get("valid", True):
                raise HTTPException(
                    status_code=400,
                    detail="El correo institucional no parece válido según verificación externa."
                )

            # Generar PIN de 6 dígitos
            generated_pin = str(random.randint(100000, 999999))
            expires_at = int((time.time() + 15 * 60) * 1000)  # 15 minutos en milisegundos

            await conn.execute("""
                INSERT INTO forum_pins (email_hash, pin, expires_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (email_hash) DO UPDATE SET
                    pin = EXCLUDED.pin,
                    expires_at = EXCLUDED.expires_at;
            """, email_hash, generated_pin, expires_at)

        # Enviar vía Resend API (community@forobuap.zrootsh.com)
        email_result = await EmailService.send_pin_email(email, generated_pin)
        email_sent = email_result.get("email_sent", False)
        error_msg = email_result.get("error")

        disable_dev_pin = settings.DISABLE_DEV_PIN
        if not email_sent and disable_dev_pin:
            raise HTTPException(
                status_code=500,
                detail=f"No se pudo enviar el correo de verificación. Detalle Resend: {error_msg or 'Servicio no disponible'}"
            )

        return {
            "success": True,
            "message": "PIN enviado a tu correo institucional." if email_sent else "PIN generado con éxito.",
            "emailSent": email_sent,
            "resendError": error_msg,
            "devPin": None if disable_dev_pin else generated_pin
        }

    # 2. VERIFICAR PIN
    if action == "verify_pin":
        if not req.email or not req.pin:
            raise HTTPException(status_code=400, detail="Correo y PIN requeridos.")

        email_hash = hash_email(req.email)
        now_ms = int(time.time() * 1000)

        if not db.pool:
            raise HTTPException(status_code=500, detail="Database not connected.")

        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM forum_pins WHERE email_hash = $1 AND pin = $2;",
                email_hash, req.pin
            )
            if not row or now_ms > row["expires_at"]:
                raise HTTPException(status_code=400, detail="PIN incorrecto o expirado.")

        return {"success": True, "message": "PIN verificado correctamente."}

    # 3. REGISTRAR USUARIO
    if action == "register":
        if not req.email or not req.pin or not req.username or not req.password:
            raise HTTPException(status_code=400, detail="Todos los campos son obligatorios.")

        if len(req.username.strip()) < 3:
            raise HTTPException(status_code=400, detail="El nombre de usuario debe tener al menos 3 caracteres.")

        if len(req.password) < 6:
            raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres.")

        clean_username = req.username.strip()
        email_hash = hash_email(req.email)
        now_ms = int(time.time() * 1000)

        if not db.pool:
            raise HTTPException(status_code=500, detail="Database not connected.")

        async with db.pool.acquire() as conn:
            # Verificar nombre de usuario único
            existing_user = await conn.fetchrow(
                "SELECT id FROM forum_users WHERE LOWER(username) = LOWER($1);",
                clean_username
            )
            if existing_user:
                raise HTTPException(status_code=400, detail="Este nombre de usuario ya está ocupado. Elige otro.")

            # Verificar PIN
            pin_record = await conn.fetchrow(
                "SELECT * FROM forum_pins WHERE email_hash = $1 AND pin = $2;",
                email_hash, req.pin
            )
            if not pin_record or now_ms > pin_record["expires_at"]:
                raise HTTPException(status_code=400, detail="El PIN de verificación es incorrecto o ha expirado.")

            # Hash de contraseña PBKDF2 sha512
            password_hash = hash_password(req.password)

            async with conn.transaction():
                await conn.execute("""
                    INSERT INTO forum_users (username, email_hash, password_hash, created_at)
                    VALUES ($1, $2, $3, NOW());
                """, clean_username, email_hash, password_hash)

                await conn.execute("DELETE FROM forum_pins WHERE email_hash = $1;", email_hash)

        return {
            "success": True,
            "user": {
                "username": clean_username,
                "emailHash": email_hash
            }
        }

    # 4. INICIAR SESIÓN
    if action == "login":
        if not req.identifier or not req.password:
            raise HTTPException(status_code=400, detail="Ingresa tu usuario/correo y contraseña.")

        clean_id = req.identifier.strip()

        if not db.pool:
            raise HTTPException(status_code=500, detail="Database not connected.")

        async with db.pool.acquire() as conn:
            if "@" in clean_id:
                email_hash = hash_email(clean_id)
                user_row = await conn.fetchrow("SELECT * FROM forum_users WHERE email_hash = $1;", email_hash)
            else:
                user_row = await conn.fetchrow("SELECT * FROM forum_users WHERE LOWER(username) = LOWER($1);", clean_id)

            if not user_row or not verify_password(req.password, user_row["password_hash"]):
                raise HTTPException(
                    status_code=401,
                    detail="Credenciales incorrectas. Verifica tu usuario/correo y contraseña."
                )

        return {
            "success": True,
            "user": {
                "username": user_row["username"],
                "emailHash": user_row["email_hash"]
            }
        }

    raise HTTPException(status_code=400, detail="Acción no válida.")
