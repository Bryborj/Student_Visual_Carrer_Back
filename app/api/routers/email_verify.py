import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.hunter_service import HunterService

router = APIRouter(tags=["VerifyEmail"])

class VerifyEmailRequest(BaseModel):
    email: str

@router.post("/verifyEmail")
async def verify_email_endpoint(req: VerifyEmailRequest):
    """Verifica la existencia y validez del correo institucional BUAP."""
    email = req.email.strip()
    if not email or not re.match(r"^\S+@\S+\.\S+$", email):
        raise HTTPException(status_code=400, detail="Correo electrónico inválido")

    domain = email.split("@")[1].lower()
    if "buap.mx" not in domain:
        raise HTTPException(status_code=400, detail="El correo debe ser institucional (contener buap.mx).")

    hunter_res = await HunterService.verify_email(email)
    if not hunter_res.get("valid", True):
        raise HTTPException(status_code=400, detail="El correo no es válido o no existe según Hunter API.")

    return {"message": "Correo verificado exitosamente", "verified": True}
