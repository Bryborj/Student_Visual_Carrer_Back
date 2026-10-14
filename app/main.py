import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import admin, auth, email_verify, forum, plans, proposals
from app.config import settings
from app.database import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("student_visual_carrer_back")

class HealthEndpointFilter(logging.Filter):
    """Filtra las consultas a /api/health para no saturar los logs de desarrollo con healthchecks periódicos."""
    def filter(self, record: logging.LogRecord) -> bool:
        return "/api/health" not in record.getMessage()

logging.getLogger("uvicorn.access").addFilter(HealthEndpointFilter())

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando backend FastAPI de Student Visual Carrer...")
    try:
        await db.connect()
        await db.init_tables()
        logger.info("Base de datos conectada e inicializada con éxito.")
    except Exception as e:
        logger.error(f"Error conectando a la base de datos al inicio: {e}")
        logger.warning("El servidor continuará ejecutándose para pruebas y endpoints sin BD.")
    yield
    logger.info("Deteniendo backend FastAPI...")
    await db.disconnect()

app = FastAPI(
    title="Student Visual Carrer API",
    description="API para el visualizador de planes de estudio BUAP, foro comunitario y gobernanza estudiantil.",
    version="2.0.0",
    lifespan=lifespan
)

# Configuración de CORS para permitir peticiones del Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar routers bajo el prefijo /api para compatibilidad exacta con el frontend
api_prefix = "/api"
app.include_router(plans.router, prefix=api_prefix)
app.include_router(auth.router, prefix=api_prefix)
app.include_router(proposals.router, prefix=api_prefix)
app.include_router(forum.router, prefix=api_prefix)
app.include_router(admin.router, prefix=api_prefix)
app.include_router(email_verify.router, prefix=api_prefix)

@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "Student_Visual_Carrer_Back",
        "version": "2.0.0",
        "email_sender": settings.RESEND_FROM_EMAIL
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEV_MODE)
