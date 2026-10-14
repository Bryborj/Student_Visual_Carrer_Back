from fastapi import Header, HTTPException

from app.database import db
from app.security import decode_access_token


async def get_current_user_from_header(
    authorization: str | None = Header(None)
) -> dict | None:
    """
    Extrae el usuario autenticado desde el token Bearer en la cabecera Authorization.
    Retorna None si no hay cabecera o si el token es inválido/expirado.
    """
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload:
        return None

    username = payload.get("sub") or payload.get("username")
    email_hash = payload.get("emailHash")
    if not username or not email_hash:
        return None

    return {"username": username, "emailHash": email_hash}


async def resolve_authenticated_user(
    authorization: str | None = None,
    body_username: str | None = None,
    body_email_hash: str | None = None,
) -> dict:
    """
    Autentica al usuario:
    1. Prioridad: Token Bearer válido en la cabecera Authorization.
    2. Fallback: Modo legado con body_username y body_email_hash, verificando existencia en base de datos.
    """
    token_user = await get_current_user_from_header(authorization)
    if token_user:
        return token_user

    # Modo legado
    if not body_username or not body_email_hash:
        raise HTTPException(
            status_code=401,
            detail="No autorizado. Inicia sesión para continuar."
        )

    if not db.pool:
        raise HTTPException(status_code=500, detail="Database not connected.")

    async with db.pool.acquire() as conn:
        user_row = await conn.fetchrow(
            "SELECT id, username, email_hash FROM forum_users WHERE LOWER(username) = LOWER($1) AND email_hash = $2;",
            body_username.strip(), body_email_hash
        )
        if not user_row:
            raise HTTPException(
                status_code=401,
                detail="Credenciales de usuario no válidas o usuario no registrado."
            )

    return {"username": user_row["username"], "emailHash": user_row["email_hash"]}
