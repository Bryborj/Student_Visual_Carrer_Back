import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

class HunterService:
    @staticmethod
    async def verify_email(email: str) -> dict:
        url = settings.emailVerifierURL
        key = settings.emailVerifierKey

        if not url or not key:
            return {"valid": True, "skipped": True, "reason": "Hunter API credentials not set"}

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(f"{url}?email={email}&api_key={key}")
                data = res.json()
                if "data" in data and "status" in data["data"]:
                    status = data["data"]["status"]
                    is_valid = status in ("valid", "accept_all")
                    return {"valid": is_valid, "status": status, "raw": data["data"]}
                return {"valid": False, "error": data.get("errors", ["Error desconocido"])}
        except Exception as e:
            logger.warning(f"Hunter verification failed due to network: {e}")
            return {"valid": True, "skipped": True, "reason": str(e)}
