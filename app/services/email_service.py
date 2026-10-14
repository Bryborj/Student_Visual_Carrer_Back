import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    async def send_pin_email(recipient_email: str, pin: str) -> dict:
        """
        Envía el código PIN de verificación institucional usando la API de Resend.
        Remitente configurado: community@forobuap.zrootsh.com
        """
        api_key = settings.RESEND_API_KEY
        from_email = settings.RESEND_FROM_EMAIL or "community@forobuap.zrootsh.com"
        from_name = settings.RESEND_FROM_NAME or "Foro Comunidad BUAP 🐺"
        sender = f"{from_name} <{from_email}>"

        html_content = f"""
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 500px; margin: 0 auto; background-color: #0f172a; color: #f8fafc; padding: 32px; border-radius: 20px; border: 1px solid #334155; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
          <div style="text-align: center; margin-bottom: 24px;">
            <div style="font-size: 48px; margin-bottom: 8px;">🐺</div>
            <h2 style="color: #c084fc; margin: 0; font-size: 24px; font-weight: 800;">Foro Comunidad BUAP</h2>
            <p style="color: #38bdf8; font-size: 13px; font-weight: 600; margin: 4px 0 0 0; text-transform: uppercase; letter-spacing: 1px;">Verificación Institucional</p>
          </div>
          
          <p style="color: #cbd5e1; font-size: 15px; line-height: 1.6; text-align: center; margin-bottom: 24px;">
            ¡Hola Lobo! Has solicitado registrarte o verificar tu cuenta institucional. Utiliza el siguiente código temporal:
          </p>
          
          <div style="background-color: #1e293b; border: 2px dashed #a855f7; border-radius: 16px; padding: 24px; text-align: center; margin: 28px 0;">
            <span style="font-size: 36px; font-weight: 900; letter-spacing: 10px; color: #38bdf8; text-shadow: 0 0 12px rgba(56, 189, 248, 0.4);">{pin}</span>
          </div>
          
          <p style="color: #94a3b8; font-size: 13px; text-align: center; margin-bottom: 8px;">
            ⏱️ Este código expirará en <strong>15 minutos</strong>.
          </p>
          <p style="color: #64748b; font-size: 12px; text-align: center; margin: 0;">
            Si no solicitaste este código, puedes ignorar este correo con tranquilidad.
          </p>
          
          <hr style="border: none; border-top: 1px solid #334155; margin: 28px 0;" />
          
          <div style="text-align: center;">
            <span style="font-size: 11px; color: #64748b; display: inline-block; background-color: #1e293b; padding: 6px 12px; border-radius: 9999px; border: 1px solid #334155;">
              🔒 Privacidad BUAP: Tu correo no se almacena en texto claro, solo conservamos una firma anónima SHA-256.
            </span>
          </div>
        </div>
        """

        if not api_key:
            logger.warning(f"⚠️ [Resend DEV] No RESEND_API_KEY configurada. PIN para {recipient_email}: {pin}")
            return {
                "success": True,
                "email_sent": False,
                "message": "PIN generado en modo desarrollo (sin API Key de Resend).",
                "dev_pin": pin
            }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": sender,
                        "to": [recipient_email],
                        "subject": "Código de Verificación PIN - Foro Comunidad BUAP 🐺",
                        "html": html_content
                    }
                )
                data = res.json()
                if res.status_code in (200, 201) and data.get("id"):
                    logger.info(f"✅ [Resend] Correo enviado a {recipient_email} con id {data.get('id')}")
                    return {"success": True, "email_sent": True, "message_id": data.get("id")}
                else:
                    error_msg = data.get("message") or str(data)
                    logger.error(f"❌ [Resend] Error de API: {error_msg}")
                    return {"success": False, "email_sent": False, "error": error_msg}
        except Exception as e:
            logger.error(f"❌ [Resend] Error de red: {e}")
            return {"success": False, "email_sent": False, "error": str(e)}

    @staticmethod
    async def send_auto_approval_notification(career: str, proposal_id: str, votes: int, author: str) -> dict:
        """
        Notifica al staff y administradores cuando una propuesta de actualización
        ha sido aprobada automáticamente por la comunidad estudiantil.
        """
        api_key = settings.RESEND_API_KEY
        admin_email = settings.ADMIN_NOTIFICATION_EMAIL or "community@forobuap.zrootsh.com"
        from_email = settings.RESEND_FROM_EMAIL or "community@forobuap.zrootsh.com"
        from_name = settings.RESEND_FROM_NAME or "Foro Comunidad BUAP 🐺"
        sender = f"{from_name} <{from_email}>"

        html_content = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; background-color: #0f172a; color: #f8fafc; padding: 32px; border-radius: 16px;">
          <h2 style="color: #4ade80;">🚀 Actualización Automática de Plan de Estudios</h2>
          <p style="color: #cbd5e1; font-size: 15px;">
            La comunidad estudiantil ha aprobado por votación una propuesta de actualización para el plan:
          </p>
          <div style="background-color: #1e293b; padding: 16px; border-radius: 8px; margin: 16px 0;">
            <p><strong>Carrera:</strong> {career}</p>
            <p><strong>Propuesta ID:</strong> {proposal_id}</p>
            <p><strong>Autor original:</strong> {author}</p>
            <p><strong>Votos a favor alcanzados:</strong> {votes}</p>
          </div>
          <p style="color: #94a3b8; font-size: 13px;">
            El cambio ha sido aplicado automáticamente a la base de datos oficial. Puedes auditar o revertir el cambio desde el Panel de Administración.
          </p>
        </div>
        """

        if not api_key:
            logger.info(f"📢 [DEV Staff Alert] Propuesta {proposal_id} para {career} auto-aprobada con {votes} votos.")
            return {"success": True, "notified": False}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": sender,
                        "to": [admin_email],
                        "subject": f"⚡ [Auto-Aprobado por Votación] Plan actualizado: {career}",
                        "html": html_content
                    }
                )
                return {"success": res.status_code in (200, 201)}
        except Exception as e:
            logger.error(f"Error enviando alerta de auto-aprobación: {e}")
            return {"success": False, "error": str(e)}
